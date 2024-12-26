import discord
from discord.ext import commands
from discord import app_commands

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="afk", description="Toggle AFK status")
    async def afk(self, interaction: discord.Interaction):
        afk_role_id = 1321561396475068536  
        guild = interaction.guild
        afk_role = guild.get_role(afk_role_id)

        if not afk_role:
            await interaction.response.send_message("AFK role not found. Please ensure the role ID is correct.", ephemeral=True)
            return

        member = interaction.user

        if afk_role in member.roles:
            await member.remove_roles(afk_role)
            await interaction.response.send_message(f"{member.mention}, you are no longer AFK.", ephemeral=True)
        else:
            await member.add_roles(afk_role)
            await interaction.response.send_message(f"{member.mention}, you are now AFK.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AFK(bot))