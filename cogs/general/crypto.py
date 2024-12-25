import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="crypto", description="Get the current price of a cryptocurrency")
    async def crypto(self, interaction: discord.Interaction, coin: str):
        print("Crypto command invoked")  # Debug print
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(f"API response status: {response.status}")  # Debug print
                if response.status == 200:
                    data = await response.json()
                    if coin in data:
                        price = data[coin]['usd']
                        embed = discord.Embed(
                            title=f"Price of {coin.capitalize()}",
                            description=f"${price} USD",
                            color=discord.Color.red()  # Light red color
                        )
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message(f"Couldn't find the price for {coin}. Please check the coin name and try again.")
                else:
                    await interaction.response.send_message("Couldn't fetch the cryptocurrency price. Please try again later.")

async def setup(bot):
    await bot.add_cog(Crypto(bot))