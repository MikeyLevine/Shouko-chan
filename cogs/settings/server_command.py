import discord
from discord.ext import commands
from discord import app_commands
import json
import os

SERVER_FILE = "data/server_list.json"
OWNER_ID = 1255466299258306611  # Your Discord ID

class ServerCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] ServerCommand cog loaded")

    @app_commands.command(
        name="server", 
        description="Get a list of all servers the bot is in with invite links"
    )
    async def server(self, interaction: discord.Interaction):
        # Only allow owner
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "You are not allowed to use this command.", ephemeral=True
            )
            return

        # Defer the response to prevent timeout
        await interaction.response.defer(ephemeral=True)

        # Delete old server file if exists
        if os.path.exists(SERVER_FILE):
            os.remove(SERVER_FILE)

        # Gather guild info
        guilds_info = []
        for guild in self.bot.guilds:
            # Try to get a general invite
            invite_url = "No permission to create invite"
            try:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).create_instant_invite:
                        invite = await channel.create_invite(max_age=0, max_uses=0, unique=True)
                        invite_url = invite.url
                        break
            except Exception as e:
                invite_url = f"Error: {e}"

            guilds_info.append({
                "id": guild.id,
                "name": guild.name,
                "member_count": guild.member_count,
                "invite": invite_url
            })

        # Save new server list
        with open(SERVER_FILE, "w", encoding="utf-8") as f:
            json.dump(guilds_info, f, indent=4, ensure_ascii=False)

        # Prepare message
        message_lines = [
            f"{g['name']} ({g['id']}) — {g['member_count']} members — Invite: {g['invite']}"
            for g in guilds_info
        ]
        message = f"Bot is in {len(guilds_info)} servers:\n" + "\n".join(message_lines)

        # If message is too long, send as a file
        if len(message) > 2000:
            file_path = "server_list.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(message)
            await interaction.followup.send(
                "Server list with invites generated. See attached file.",
                file=discord.File(file_path),
                ephemeral=True
            )
            os.remove(file_path)
        else:
            await interaction.followup.send(message, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ServerCommand(bot))
