import discord
from discord.ext import commands
from discord import app_commands
import random

class Roll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Roll cog loaded")

    @app_commands.command(name="roll", description="Roll a number between 1 and 100")
    async def roll(self, interaction: discord.Interaction):
        result = random.randint(1, 100)

        embed = discord.Embed(
            title="🎲 Dice Roll",
            description=f"**You rolled:** {result}",
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Roll(bot))
