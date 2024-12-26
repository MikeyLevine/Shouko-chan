import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help for all commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Help",
            description="List of all available commands",
            color=discord.Color.blue()
        )

        for command in self.bot.tree.walk_commands():
            embed.add_field(
                name=f"/{command.name}",
                value=command.description or "No description provided",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))