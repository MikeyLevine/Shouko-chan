import discord
from discord.ext import commands
from discord import app_commands

class Shutdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shutdown", description="Shut down the bot")
    async def shutdown(self, interaction: discord.Interaction):
        authorized_user_id = 1255466299258306611
        if interaction.user.id != authorized_user_id:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        await interaction.response.send_message("Shutting down the bot...")
        await self.bot.close()

async def setup(bot):
    await bot.add_cog(Shutdown(bot))