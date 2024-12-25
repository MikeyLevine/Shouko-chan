import discord
from discord.ext import commands
from discord import app_commands

class Hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Say hello")
    async def hello(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Hello!",
            description="Hello!",
            color=discord.Color.red()  # Light red color
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Hello(bot))