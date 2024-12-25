import discord
from discord.ext import commands
from discord import app_commands

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency = self.bot.latency
        embed = discord.Embed(
            title="Pong!",
            description=f"Latency: {latency*1000:.2f} ms",
            color=discord.Color.green()  # Light green color
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Ping(bot))