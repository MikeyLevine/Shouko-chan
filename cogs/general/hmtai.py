import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp
from bs4 import BeautifulSoup

BASE_URL = "http://24.135.112.94:8080"
CATEGORIES = [
    "anal", "ass", "bdsm", "blowjob", "boobs", "cum",
    "gangbang", "handjob", "masturbation", "neko", "paizuri",
    "piss", "pussy", "tentacle", "thighs", "trap", "waifu",
    "yaoi", "yuri"
]

class HMTai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] HMTai cog loaded")  # Debug output

    @app_commands.command(name="hentai", description="Get a hentai GIF from local server")
    async def hentai(self, interaction: discord.Interaction, category: str):
        category = category.lower()
        if category not in CATEGORIES:
            await interaction.response.send_message(
                f"❌ Invalid category '{category}'.\nAvailable: {', '.join(CATEGORIES)}",
                ephemeral=True
            )
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/{category}/") as resp:
                    if resp.status != 200:
                        await interaction.response.send_message(
                            f"⚠️ Cannot reach image server for category '{category}'.",
                            ephemeral=True
                        )
                        return

                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")

                    links = [
                        a.get("href") for a in soup.find_all("a")
                        if a.get("href") and a.get("href").lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
                    ]

                    if not links:
                        await interaction.response.send_message(
                            f"⚠️ No files found in category '{category}'!", ephemeral=True
                        )
                        return

                    file_name = random.choice(links).lstrip("/").replace(" ", "%20")
                    file_url = f"{BASE_URL}/{category}/{file_name}"

        except aiohttp.ClientError as e:
            await interaction.response.send_message(f"❌ HTTP error: {e}", ephemeral=True)
            print(f"[ERROR] HTTP error in HMTai: {e}")
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Unexpected error: {e}", ephemeral=True)
            print(f"[ERROR] Unexpected in HMTai: {e}")
            return

        embed = discord.Embed(
            title=f"Hentai - {category.capitalize()}",
            color=discord.Color.red()
        )
        embed.set_image(url=file_url)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(HMTai(bot))
