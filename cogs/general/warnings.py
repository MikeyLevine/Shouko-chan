import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings = self.load_warnings()

    def load_warnings(self):
        if os.path.exists("warnings.json"):
            with open("warnings.json", "r") as f:
                return json.load(f)
        return {}

    def save_warnings(self):
        with open("warnings.json", "w") as f:
            json.dump(self.warnings, f)

    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if str(user.id) not in self.warnings:
            self.warnings[str(user.id)] = []
        self.warnings[str(user.id)].append(reason)
        self.save_warnings()
        await interaction.response.send_message(f"{user.mention} has been warned for: {reason}", ephemeral=True)

    @app_commands.command(name="warnings", description="View warnings for a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        if str(user.id) in self.warnings:
            warnings_list = "\n".join(self.warnings[str(user.id)])
            await interaction.response.send_message(f"{user.mention} has the following warnings:\n{warnings_list}", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.mention} has no warnings.", ephemeral=True)

    @app_commands.command(name="warnremove", description="Remove all warnings for a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def warnremove(self, interaction: discord.Interaction, user: discord.Member):
        if str(user.id) in self.warnings:
            del self.warnings[str(user.id)]
            self.save_warnings()
            await interaction.response.send_message(f"All warnings for {user.mention} have been removed.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.mention} has no warnings.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Warnings(bot))