import discord
from discord.ext import commands
from discord import app_commands
import requests

class HMTai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hentai", description="Get an image from the HMTai API")
    async def hentai(self, interaction: discord.Interaction, category: str):
        try:
            url = f"https://hmtai.hatsunia.cfd/v2/{category}"
            response = requests.get(url)
            if response.status_code == 200:  # Use status_code instead of status
                data = response.json()
                image_url = data['url']
                embed = discord.Embed(
                    title=f"HMTai - {category.capitalize()}",
                    color=discord.Color.red()
                )
                embed.set_image(url=image_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("Couldn't fetch the image. Please try again later.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HMTai(bot))