import discord
from discord.ext import commands
from discord import app_commands
import re

class React(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] React cog loaded")

    @app_commands.command(name="react", description="Add letter(s) as reaction to a previous message")
    async def react(self, interaction: discord.Interaction, message_identifier: str, emojis: str):
        """
        Add letter(s) as reaction to previous message.
        message_identifier can be:
        - Message ID from current channel
        - Jump URL 
        - channel_id-message_id format
        """
        try:
            message = None

            # Jump URL
            if 'discord.com/channels/' in message_identifier:
                match = re.search(r'/(\d+)/(\d+)$', message_identifier)
                if match:
                    channel_id, msg_id = map(int, match.groups())
                    channel = interaction.guild.get_channel(channel_id)
                    if channel:
                        message = await channel.fetch_message(msg_id)

            # channelID-messageID format
            elif '-' in message_identifier and len(message_identifier) > 17:
                parts = message_identifier.split('-')
                if len(parts) == 2 and all(part.isdigit() for part in parts):
                    channel_id, msg_id = map(int, parts)
                    channel = interaction.guild.get_channel(channel_id)
                    if channel:
                        message = await channel.fetch_message(msg_id)

            # Just message ID
            else:
                try:
                    msg_id = int(message_identifier)
                    message = await interaction.channel.fetch_message(msg_id)
                except (ValueError, discord.NotFound):
                    await interaction.response.send_message("❌ Invalid message identifier provided.", ephemeral=True)
                    return

            if not message:
                await interaction.response.send_message("❌ Could not find the specified message.", ephemeral=True)
                return

            # Add reactions
            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)
                except discord.HTTPException:
                    pass

            await interaction.response.send_message(f"✅ Added reactions '{emojis}' to message.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"⚠️ An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(React(bot))
