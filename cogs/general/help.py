import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="List all commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Help - List of Commands",
            description="Here are the available commands:",
            color=discord.Color.blue()
        )
        
        for command in self.bot.tree.walk_commands():
            if command.name == "shutdown":
                continue
            embed.add_field(name=f"/{command.name}", value=command.description, inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))