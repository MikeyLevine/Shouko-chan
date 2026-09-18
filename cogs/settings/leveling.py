import discord
from discord.ext import commands
from discord import app_commands
import time

import db
from cogs.profile.card import generate_leaderboard_card

DEFAULT_COOLDOWN = 8 * 60


class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_exp_time = {}
        print("[DEBUG] Leveling cog loaded")  # Debug output on cog load

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

    def _cooldown_for(self, guild_id):
        row = db.connection.execute(
            "SELECT cooldown_time FROM server_settings WHERE guild_id = ?", (str(guild_id),)
        ).fetchone()
        return row["cooldown_time"] if row else DEFAULT_COOLDOWN

    def ensure_user(self, guild_id, user_id):
        guild_id, user_id = str(guild_id), str(user_id)
        row = db.connection.execute(
            "SELECT * FROM leveling_accounts WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ).fetchone()
        if row is None:
            db.connection.execute(
                "INSERT INTO leveling_accounts (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id)
            )
            db.connection.commit()
            row = db.connection.execute(
                "SELECT * FROM leveling_accounts WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
            ).fetchone()
        return row

    def get_exp(self, guild_id, user_id):
        return self.ensure_user(guild_id, user_id)["exp"]

    def set_exp(self, guild_id, user_id, new_exp):
        """Used by /grant. Returns (exp, level) after clamping to >= 0."""
        guild_id, user_id = str(guild_id), str(user_id)
        new_exp = max(0, new_exp)
        new_level = self.calculate_level(new_exp)
        self.ensure_user(guild_id, user_id)
        db.connection.execute(
            "UPDATE leveling_accounts SET exp = ?, level = ? WHERE guild_id = ? AND user_id = ?",
            (new_exp, new_level, guild_id, user_id)
        )
        db.connection.commit()
        return new_exp, new_level

    def get_rank(self, guild_id, user_id):
        """Returns (rank_or_None, total_ranked_in_guild) - used by /profile."""
        guild_id, user_id = str(guild_id), str(user_id)
        rows = db.connection.execute(
            "SELECT user_id FROM leveling_accounts WHERE guild_id = ? ORDER BY exp DESC", (guild_id,)
        ).fetchall()
        for i, row in enumerate(rows, start=1):
            if row["user_id"] == user_id:
                return i, len(rows)
        return None, len(rows)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        current_time = time.time()

        key = (guild_id, user_id)
        last_time = self.last_exp_time.get(key)
        if last_time is not None and current_time - last_time < self._cooldown_for(guild_id):
            return

        row = self.ensure_user(guild_id, user_id)
        if not row["enabled"]:
            return

        new_exp = row["exp"] + 10
        new_level = self.calculate_level(new_exp)
        db.connection.execute(
            "UPDATE leveling_accounts SET exp = ?, level = ? WHERE guild_id = ? AND user_id = ?",
            (new_exp, new_level, guild_id, user_id)
        )
        db.connection.commit()

        if new_level > row["level"]:
            print(f"[DEBUG] {message.author} leveled up to {new_level} in {message.guild}")  # Debug output
            await self.send_level_up_message(message.channel, message.author, new_level)

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

        row = db.connection.execute(
            "SELECT exp, level FROM leveling_accounts WHERE guild_id = ? AND user_id = ?",
            (str(interaction.guild.id), str(interaction.user.id))
        ).fetchone()
        if row:
            embed = discord.Embed(
                title="Your Level",
                description=f"{interaction.user.mention}, you are currently at level {row['level']} with {row['exp']} experience points in **{interaction.guild.name}**.",
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

        row = self.ensure_user(interaction.guild.id, interaction.user.id)
        new_enabled = 0 if row["enabled"] else 1
        db.connection.execute(
            "UPDATE leveling_accounts SET enabled = ? WHERE guild_id = ? AND user_id = ?",
            (new_enabled, str(interaction.guild.id), str(interaction.user.id))
        )
        db.connection.commit()
        status = "activated" if new_enabled else "deactivated"
        print(f"[DEBUG] {interaction.user} toggled leveling: {status} in {interaction.guild}")  # Debug

        await interaction.response.send_message(f"Leveling system has been {status} for you in this server.", ephemeral=True)

    @app_commands.command(name="set_cooldown", description="Set the cooldown time for experience points (in minutes)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_cooldown(self, interaction: discord.Interaction, cooldown_time: int):
        db.connection.execute(
            "INSERT INTO server_settings (guild_id, cooldown_time) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET cooldown_time = excluded.cooldown_time",
            (str(interaction.guild.id), cooldown_time * 60)
        )
        db.connection.commit()
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
            rows = db.connection.execute(
                "SELECT user_id, exp, level FROM leveling_accounts WHERE guild_id = ? ORDER BY exp DESC LIMIT 10",
                (str(interaction.guild.id),)
            ).fetchall()
            title = f"Leaderboard - {interaction.guild.name}"
        else:
            raw_rows = db.connection.execute(
                "SELECT user_id, SUM(exp) AS exp FROM leveling_accounts GROUP BY user_id ORDER BY exp DESC LIMIT 10"
            ).fetchall()
            rows = [{"user_id": r["user_id"], "exp": r["exp"], "level": self.calculate_level(r["exp"])} for r in raw_rows]
            title = "Global Leaderboard (all servers combined)"

        if not rows:
            await interaction.response.send_message("No leveling data yet.", ephemeral=True)
            return

        await interaction.response.defer()

        entries = []
        for rank, row in enumerate(rows, start=1):
            user = self.bot.get_user(int(row["user_id"]))
            name = user.display_name if user else f"Unknown User ({row['user_id']})"
            avatar_bytes = None
            if user:
                try:
                    avatar_bytes = await user.display_avatar.with_size(128).read()
                except discord.HTTPException:
                    avatar_bytes = None
            entries.append({
                "rank": rank, "name": name, "avatar_bytes": avatar_bytes,
                "value_text": f"Level {row['level']} • {row['exp']} XP"
            })

        buffer = generate_leaderboard_card(title, entries)
        await interaction.followup.send(file=discord.File(buffer, filename="leaderboard.png"))

async def setup(bot):
    await bot.add_cog(Leveling(bot))
