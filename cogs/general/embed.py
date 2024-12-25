import discord
from discord.ext import commands
from discord import app_commands

class Embed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="Create an embedded post")
    async def embed(self, interaction: discord.Interaction, title: str, description: str, color: str = "blue"):
        try:
            # Convert color string to discord.Color
            color_dict = {
                "blue": discord.Color.blue(),
                "red": discord.Color.red(),
                "green": discord.Color.green(),
                "yellow": discord.Color.yellow(),
                "purple": discord.Color.purple(),
                "orange": discord.Color.orange(),
                "random": discord.Color.random()
            }
            embed_color = color_dict.get(color.lower(), discord.Color.blue())

            embed = discord.Embed(
                title=title,
                description=description,
                color=embed_color
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Embed(bot))