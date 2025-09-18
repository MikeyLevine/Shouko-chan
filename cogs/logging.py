import discord
from discord.ext import commands

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Logging cog loaded")  # Added debug output

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        print(f"[DEBUG] Message deleted: {message.content}")  # Updated debug format

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        print(f"[DEBUG] Message edited from: {before.content} to: {after.content}")  # Updated debug format

async def setup(bot):
    await bot.add_cog(Logging(bot))
