import discord
from discord.ext import commands

class RichPresence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            activity = discord.Streaming(name="Streaming on Twitch", url="https://www.twitch.tv/EnigmaticEon")
            await self.bot.change_presence(status=discord.Status.online, activity=activity)
        except Exception as e:
            print(f"Failed to set bot status: {e}")

async def setup(bot):
    await bot.add_cog(RichPresence(bot))