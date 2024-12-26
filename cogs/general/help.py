import discord
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", description="Show help for all commands")
    async def help(self, ctx):
        embed = discord.Embed(
            title="Help",
            description="List of all available commands",
            color=discord.Color.blue()
        )

        for command in self.bot.commands:
            embed.add_field(
                name=f"/{command.name}",
                value=command.description or "No description provided",
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))