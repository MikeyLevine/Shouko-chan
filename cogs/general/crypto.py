import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
CRYPTO_API_KEY = os.getenv("CRYPTO_API_KEY")  # from your .env

class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Crypto cog loaded")  # debug output on cog load

    @app_commands.command(name="crypto", description="Get the current price of a cryptocurrency")
    async def crypto(self, interaction: discord.Interaction, coin: str):
        coin = coin.upper()  # normalize input
        print(f"[DEBUG] /crypto command invoked for: {coin}")

        url = f"https://api.coinbase.com/v2/prices/{coin}-USD/spot"
        headers = {}
        if CRYPTO_API_KEY:
            headers["Authorization"] = f"Bearer {CRYPTO_API_KEY}"

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    print(f"[DEBUG] API response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        if "data" in data and "amount" in data["data"]:
                            price = data["data"]["amount"]
                            embed = discord.Embed(
                                title=f"{coin} Price",
                                description=f"${price} USD",
                                color=discord.Color.green()
                            )
                            await interaction.response.send_message(embed=embed)
                            print(f"[DEBUG] Sent price for {coin}: ${price}")
                        else:
                            await interaction.response.send_message(
                                f"❌ Couldn't find the price for {coin}. Check the symbol and try again.",
                                ephemeral=True
                            )
                            print(f"[DEBUG] No price data found for {coin}")
                    else:
                        await interaction.response.send_message(
                            "⚠️ Couldn't fetch the cryptocurrency price. Please try again later.",
                            ephemeral=True
                        )
                        print(f"[DEBUG] API returned status {response.status}")
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)
            print(f"[ERROR] Exception in /crypto command: {e}")

async def setup(bot):
    await bot.add_cog(Crypto(bot))
