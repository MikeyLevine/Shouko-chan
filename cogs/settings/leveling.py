import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_data = self.load_user_data()
        self.server_settings = self.load_server_settings()
        self.last_exp_time = {}
        print("[DEBUG] Leveling cog loaded")  # Debug output on cog load

    def load_user_data(self):
        # Data shape: {guild_id: {user_id: {"exp": int, "level": int, "enabled": bool}}}
        if not os.path.exists("data/user_data.json"):
            return {}
        with open("data/user_data.json", "r") as f:
            data = json.load(f)
        if self._is_legacy_format(data):
            # Old format was a flat {user_id: {...}} with no guild attached at
            # all (leveling used to be tracked globally). There's no correct
            # guild to attribute that history to, so start fresh per-server.
            print("[DEBUG] Migrating leveling data from legacy global format - starting fresh per-server data")
            return {}
        return data

    @staticmethod
    def _is_legacy_format(data):
        for value in data.values():
            return isinstance(value, dict) and "exp" in value
        return False

    def save_user_data(self):
        with open("data/user_data.json", "w") as f:
            json.dump(self.user_data, f, indent=4)

    def load_server_settings(self):
        if os.path.exists("data/server_settings.json"):
            with open("data/server_settings.json", "r") as f:
                return json.load(f)
        return {}

    def save_server_settings(self):
        with open("data/server_settings.json", "w") as f:
            json.dump(self.server_settings, f, indent=4)

    def calculate_level(self, exp):
        level, _, _ = self.get_level_progress(exp)
        return level

    def get_level_progress(self, exp):
        """Returns (level, exp accumulated within that level, exp needed to
        reach the next level) - used for the /profile XP progress bar."""
        level = 1
        required_exp = 100
        while exp >= required_exp:
            exp -= required_exp
            level += 1
            required_exp = level * 100
        return level, exp, required_exp

    def get_user_entry(self, guild_id, user_id):
        guild_id, user_id = str(guild_id), str(user_id)
        guild_data = self.user_data.setdefault(guild_id, {})
        if user_id not in guild_data:
            guild_data[user_id] = {"exp": 0, "level": 1, "enabled": True}
        return guild_data[user_id]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        current_time = time.time()

        cooldown_time = self.server_settings.get(guild_id, {}).get("cooldown_time", 8 * 60)

        key = (guild_id, user_id)
        last_time = self.last_exp_time.get(key)
        if last_time is not None and current_time - last_time < cooldown_time:
            return

        entry = self.get_user_entry(guild_id, user_id)
        if not entry.get("enabled", True):
            return

        entry["exp"] += 10
        new_level = self.calculate_level(entry["exp"])

        if new_level > entry["level"]:
            entry["level"] = new_level
            print(f"[DEBUG] {message.author} leveled up to {new_level} in {message.guild}")  # Debug output
            await self.send_level_up_message(message.channel, message.author, new_level)

        self.save_user_data()
        self.last_exp_time[key] = current_time

    async def send_level_up_message(self, channel, user, level):
        embed = discord.Embed(
            title="Level Up!",
            description=f"Congratulations {user.mention}, you have reached level {level}!",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)

    @app_commands.command(name="check_level", description="Check your current level and experience points")
    async def check_level(self, interaction: discord.Interaction):
        print(f"[DEBUG] check_level command invoked by {interaction.user}")  # Debug
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        entry = self.user_data.get(str(interaction.guild.id), {}).get(str(interaction.user.id))
        if entry:
            embed = discord.Embed(
                title="Your Level",
                description=f"{interaction.user.mention}, you are currently at level {entry['level']} with {entry['exp']} experience points in **{interaction.guild.name}**.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="No Data",
                description=f"{interaction.user.mention}, you have no experience points yet in **{interaction.guild.name}**.",
                color=discord.Color.red()
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="toggle_leveling", description="Activate or deactivate the leveling system for yourself in this server")
    async def toggle_leveling(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        entry = self.get_user_entry(interaction.guild.id, interaction.user.id)
        entry["enabled"] = not entry.get("enabled", True)
        status = "activated" if entry["enabled"] else "deactivated"
        self.save_user_data()
        print(f"[DEBUG] {interaction.user} toggled leveling: {status} in {interaction.guild}")  # Debug

        await interaction.response.send_message(f"Leveling system has been {status} for you in this server.", ephemeral=True)

    @app_commands.command(name="set_cooldown", description="Set the cooldown time for experience points (in minutes)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_cooldown(self, interaction: discord.Interaction, cooldown_time: int):
        guild_id = str(interaction.guild.id)
        self.server_settings.setdefault(guild_id, {})["cooldown_time"] = cooldown_time * 60
        self.save_server_settings()
        print(f"[DEBUG] Cooldown set to {cooldown_time} minutes for guild {interaction.guild}")  # Debug

        await interaction.response.send_message(f"Cooldown time has been set to {cooldown_time} minutes.", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the leveling leaderboard")
    @app_commands.describe(scope="This server only, or aggregated across every server the bot is in")
    @app_commands.choices(scope=[
        app_commands.Choice(name="This server", value="server"),
        app_commands.Choice(name="Global (all servers)", value="global"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, scope: app_commands.Choice[str] = None):
        scope_value = scope.value if scope else "server"

        if scope_value == "server":
            if not interaction.guild:
                await interaction.response.send_message("Server scope only works inside a server.", ephemeral=True)
                return
            guild_data = self.user_data.get(str(interaction.guild.id), {})
            ranked = sorted(guild_data.items(), key=lambda item: item[1].get("exp", 0), reverse=True)
            title = f"🏆 Leaderboard - {interaction.guild.name}"
        else:
            totals = {}
            for guild_data in self.user_data.values():
                for user_id, entry in guild_data.items():
                    totals[user_id] = totals.get(user_id, 0) + entry.get("exp", 0)
            ranked = [
                (user_id, {"exp": exp, "level": self.calculate_level(exp)})
                for user_id, exp in sorted(totals.items(), key=lambda item: item[1], reverse=True)
            ]
            title = "🏆 Global Leaderboard (all servers combined)"

        if not ranked:
            await interaction.response.send_message("No leveling data yet.", ephemeral=True)
            return

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = []
        for rank, (user_id, entry) in enumerate(ranked[:10], start=1):
            user = self.bot.get_user(int(user_id))
            name = user.display_name if user else f"Unknown User ({user_id})"
            lines.append(f"{medals.get(rank, f'#{rank}')} **{name}** - Level {entry['level']} - {entry['exp']} XP")

        embed = discord.Embed(title=title, description="\n".join(lines), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
