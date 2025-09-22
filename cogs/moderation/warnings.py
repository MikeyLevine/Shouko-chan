import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings = self.load_warnings()
        print("[DEBUG] Warnings cog loaded")  # Debug output

    def load_warnings(self):
        if os.path.exists("data/warnings.json"):
            with open("data/warnings.json", "r") as f:
                data = json.load(f)
            print(f"[DEBUG] Loaded warnings data: {data}")  # Debug
            return data
        return {}

    def save_warnings(self):
        with open("data/warnings.json", "w") as f:
            json.dump(self.warnings, f)
        print(f"[DEBUG] Saved warnings data: {self.warnings}")  # Debug

    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        self.warnings.setdefault(str(user.id), []).append(reason)
        self.save_warnings()
        await interaction.response.send_message(f"{user.mention} has been warned for: {reason}", ephemeral=True)
        print(f"[DEBUG] {user} warned for: {reason}")  # Debug

    @app_commands.command(name="warnings", description="View warnings for a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        if str(user.id) in self.warnings and self.warnings[str(user.id)]:
            warnings_list = "\n".join(self.warnings[str(user.id)])
            await interaction.response.send_message(f"{user.mention} has the following warnings:\n{warnings_list}", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.mention} has no warnings.", ephemeral=True)
        print(f"[DEBUG] Warnings viewed for {user}")  # Debug

    @app_commands.command(name="warnremove", description="Remove all warnings for a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def warnremove(self, interaction: discord.Interaction, user: discord.Member):
        if str(user.id) in self.warnings:
            del self.warnings[str(user.id)]
            self.save_warnings()
            await interaction.response.send_message(f"All warnings for {user.mention} have been removed.", ephemeral=True)
            print(f"[DEBUG] Warnings removed for {user}")  # Debug
        else:
            await interaction.response.send_message(f"{user.mention} has no warnings.", ephemeral=True)
            print(f"[DEBUG] No warnings to remove for {user}")  # Debug

async def setup(bot):
    await bot.add_cog(Warnings(bot))
