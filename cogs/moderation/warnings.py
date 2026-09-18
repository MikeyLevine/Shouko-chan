import discord
from discord.ext import commands
from discord import app_commands

import db

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Warnings cog loaded")  # Debug output

    def get_warnings(self, user_id):
        rows = db.connection.execute(
            "SELECT reason FROM warnings WHERE user_id = ? ORDER BY id", (str(user_id),)
        ).fetchall()
        return [r["reason"] for r in rows]

    async def warn_manual(self, guild_id, member, reason):
        """Programmatic warn used by automod's auto-escalation - not a slash
        command. (guild_id is unused: warnings are tracked globally per
        user, same pre-existing behavior as before this migration.)"""
        db.connection.execute("INSERT INTO warnings (user_id, reason) VALUES (?, ?)", (str(member.id), reason))
        db.connection.commit()

    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        db.connection.execute("INSERT INTO warnings (user_id, reason) VALUES (?, ?)", (str(user.id), reason))
        db.connection.commit()
        await interaction.response.send_message(f"{user.mention} has been warned for: {reason}", ephemeral=True)
        print(f"[DEBUG] {user} warned for: {reason}")  # Debug

    @app_commands.command(name="warnings", description="View warnings for a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        reasons = self.get_warnings(user.id)
        if reasons:
            warnings_list = "\n".join(reasons)
            await interaction.response.send_message(f"{user.mention} has the following warnings:\n{warnings_list}", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.mention} has no warnings.", ephemeral=True)
        print(f"[DEBUG] Warnings viewed for {user}")  # Debug

    @app_commands.command(name="warnremove", description="Remove all warnings for a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def warnremove(self, interaction: discord.Interaction, user: discord.Member):
        if self.get_warnings(user.id):
            db.connection.execute("DELETE FROM warnings WHERE user_id = ?", (str(user.id),))
            db.connection.commit()
            await interaction.response.send_message(f"All warnings for {user.mention} have been removed.", ephemeral=True)
            print(f"[DEBUG] Warnings removed for {user}")  # Debug
        else:
            await interaction.response.send_message(f"{user.mention} has no warnings.", ephemeral=True)
            print(f"[DEBUG] No warnings to remove for {user}")  # Debug

async def setup(bot):
    await bot.add_cog(Warnings(bot))
