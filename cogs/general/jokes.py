import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

class Jokes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Jokes cog loaded")  # Debug output on load

    @app_commands.command(name="joke", description="Get a random joke")
    async def joke(self, interaction: discord.Interaction):
        url = "https://official-joke-api.appspot.com/random_joke"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    setup = data['setup']
                    punchline = data['punchline']
                    embed = discord.Embed(
                        title="Here's a joke for you!",
                        description=f"{setup}\n\n{punchline}",
                        color=discord.Color.orange()
                    )
                    await interaction.response.send_message(embed=embed)
                else:
                    embed = discord.Embed(
                        title="Error",
                        description="Couldn't fetch a joke. Please try again later.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Jokes(bot))
