import discord
from discord.ext import commands
import json
import os

SERVER_FILE = "data/server_list.json"
OWNER_ID = 1255466299258306611  # Your Discord ID

class ServerNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] ServerNotify cog loaded")

    async def update_server_list(self):
        """Update server_list.json with current guilds."""
        guilds_info = [{"id": g.id, "name": g.name, "member_count": g.member_count} for g in self.bot.guilds]
        with open(SERVER_FILE, "w") as f:
            json.dump(guilds_info, f, indent=4)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # Update server_list.json
        await self.update_server_list()

        # DM owner with new server info
        owner = await self.bot.fetch_user(OWNER_ID)
        invite = None
        try:
            # Try to find a general text channel to create an invite
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).create_instant_invite:
                    invite = await channel.create_invite(max_age=3600, max_uses=1)
                    break
        except Exception:
            invite = None

        msg = f"Bot was added to server:\n**{guild.name}** ({guild.id}) — {guild.member_count} members"
        if invite:
            msg += f"\nInvite: {invite.url}"

        await owner.send(msg)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        # Update server_list.json
        await self.update_server_list()

async def setup(bot):
    await bot.add_cog(ServerNotify(bot))

