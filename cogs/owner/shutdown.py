import discord
from discord.ext import commands
from discord import app_commands

AUTHORIZED_USER_ID = 1255466299258306611

class Shutdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Shutdown cog loaded")  # Debug output

    @app_commands.command(name="shutdown", description="Shut down the bot")
    async def shutdown(self, interaction: discord.Interaction):
        if interaction.user.id != AUTHORIZED_USER_ID:
            await interaction.response.send_message(
                "You are not authorized to use this command.", ephemeral=True
            )
            print(f"[DEBUG] Unauthorized shutdown attempt by {interaction.user}")  # Debug
            return
        
        await interaction.response.send_message("Shutting down the bot...")
        print(f"[DEBUG] Bot shutdown initiated by {interaction.user}")  # Debug
        await self.bot.close()

async def setup(bot):
    await bot.add_cog(Shutdown(bot))
