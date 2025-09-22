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
        if os.path.exists("data/user_data.json"):
            with open("data/user_data.json", "r") as f:
                return json.load(f)
        return {}

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
        level = 1
        required_exp = 100
        while exp >= required_exp:
            exp -= required_exp
            level += 1
            required_exp = level * 100
        return level

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        current_time = time.time()

        cooldown_time = self.server_settings.get(guild_id, {}).get("cooldown_time", 8 * 60)

        if user_id in self.last_exp_time:
            last_time = self.last_exp_time[user_id]
            if current_time - last_time < cooldown_time:
                return

        if user_id not in self.user_data:
            self.user_data[user_id] = {"exp": 0, "level": 1, "enabled": True}

        if not self.user_data[user_id].get("enabled", True):
            return

        self.user_data[user_id]["exp"] += 10
        new_level = self.calculate_level(self.user_data[user_id]["exp"])

        if new_level > self.user_data[user_id]["level"]:
            self.user_data[user_id]["level"] = new_level
            print(f"[DEBUG] {message.author} leveled up to {new_level}")  # Debug output
            await self.send_level_up_message(message.channel, message.author, new_level)

        self.save_user_data()
        self.last_exp_time[user_id] = current_time

    async def send_level_up_message(self, channel, user, level):
        embed = discord.Embed(
            title="Level Up!",
            description=f"Congratulations {user.mention}, you have reached level {level}!",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)

    @app_commands.command(name="check_level", description="Check your current level and experience points")
    async def check_level(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        print(f"[DEBUG] check_level command invoked by {interaction.user}")  # Debug
        if user_id in self.user_data:
            exp = self.user_data[user_id]["exp"]
            level = self.user_data[user_id]["level"]
            embed = discord.Embed(
                title="Your Level",
                description=f"{interaction.user.mention}, you are currently at level {level} with {exp} experience points.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="No Data",
                description=f"{interaction.user.mention}, you have no experience points yet.",
                color=discord.Color.red()
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="toggle_leveling", description="Activate or deactivate the leveling system for yourself")
    async def toggle_leveling(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.user_data:
            self.user_data[user_id] = {"exp": 0, "level": 1, "enabled": True}

        self.user_data[user_id]["enabled"] = not self.user_data[user_id].get("enabled", True)
        status = "activated" if self.user_data[user_id]["enabled"] else "deactivated"
        self.save_user_data()
        print(f"[DEBUG] {interaction.user} toggled leveling: {status}")  # Debug

        await interaction.response.send_message(f"Leveling system has been {status} for you.", ephemeral=True)

    @app_commands.command(name="set_cooldown", description="Set the cooldown time for experience points (in minutes)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_cooldown(self, interaction: discord.Interaction, cooldown_time: int):
        guild_id = str(interaction.guild.id)
        if guild_id not in self.server_settings:
            self.server_settings[guild_id] = {}

        self.server_settings[guild_id]["cooldown_time"] = cooldown_time * 60
        self.save_server_settings()
        print(f"[DEBUG] Cooldown set to {cooldown_time} minutes for guild {interaction.guild}")  # Debug

        await interaction.response.send_message(f"Cooldown time has been set to {cooldown_time} minutes.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
