import discord
from discord.ext import commands
from discord import app_commands

OWNER_ID = 1255466299258306611  # Replace with your Discord user ID

class OwnerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_owner(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID

    @app_commands.command(name="type", description="Send a message in a server channel")
    @app_commands.check(is_owner)
    async def type(self, interaction: discord.Interaction, channel_id: str, message: str):
        try:
            channel_id = int(channel_id)  # Ensure channel_id is an integer
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(message)
                await interaction.response.send_message(f"Message sent to {channel.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("Channel not found. Please check the channel ID.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Channel ID must be an integer.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="dm", description="Send a direct message to a user")
    @app_commands.check(is_owner)
    async def dm(self, interaction: discord.Interaction, user_id: str, message: str):
        try:
            user_id = int(user_id)  # Ensure user_id is an integer
            user = await self.bot.fetch_user(user_id)
            if user:
                await user.send(message)
                await interaction.response.send_message(f"Message sent to {user.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("User not found. Please check the user ID.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("User ID must be an integer.", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("User not found. Please check the user ID.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Cannot send message to this user. They might have DMs disabled.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @type.error
    @dm.error
    async def owner_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(OwnerCommands(bot))