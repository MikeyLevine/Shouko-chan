import discord
from discord.ext import commands

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        print(f"Message deleted: {message.content}")  # Debug print

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        print(f"Message edited from: {before.content} to: {after.content}")  # Debug print

async def setup(bot):
    await bot.add_cog(Logging(bot))
