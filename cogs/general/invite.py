import discord
from discord.ext import commands
from discord import app_commands

class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Get the Discord invite link")
    async def invite(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Join Our Discord Server",
            description="Click the button below to join our Discord server!",
            color=discord.Color.blue()
        )
        
        # Button with the Discord invite link
        button = discord.ui.Button(label="Join Now", url="https://discord.gg/4tp457CRD8")
        view = discord.ui.View()
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Invite(bot))