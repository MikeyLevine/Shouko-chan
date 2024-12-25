import discord
from discord.ext import commands, tasks

class Presence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.set_presence.start()

    def cog_unload(self):
        self.set_presence.cancel()

    @tasks.loop(minutes=5)
    async def set_presence(self):
        await self.bot.change_presence(activity=discord.Game(name="Early Development | Join: https://discord.gg/4tp457CRD8"))

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Logged on as {self.bot.user}!')

    @commands.command(name="invite", description="Get the bot invite link")
    async def invite(self, ctx):
        embed = discord.Embed(
            title="In Development",
            description="Join our server",
            color=discord.Color.blue()
        )
        button = discord.ui.Button(label="Join", url="https://discord.gg/4tp457CRD8")

        view = discord.ui.View()
        view.add_item(button)

        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Presence(bot))