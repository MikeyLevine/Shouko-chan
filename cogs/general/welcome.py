import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Welcome cog loaded")  # Debug output

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = discord.utils.get(member.guild.text_channels, name='welcome')
        if channel:
            await channel.send(f'Welcome to the server, {member.mention}!')
            print(f"[DEBUG] Sent welcome message to {member}")  # Debug
        else:
            print("[DEBUG] Welcome channel not found")  # Debug

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = discord.utils.get(member.guild.text_channels, name='goodbye')
        if channel:
            await channel.send(f'Goodbye, {member.mention}. We will miss you!')
            print(f"[DEBUG] Sent goodbye message to {member}")  # Debug
        else:
            print("[DEBUG] Goodbye channel not found")  # Debug

async def setup(bot):
    await bot.add_cog(Welcome(bot))
