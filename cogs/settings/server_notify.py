import discord
from discord.ext import commands

import db

OWNER_ID = 1255466299258306611  # Your Discord ID

class ServerNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] ServerNotify cog loaded")

    def update_server_list(self):
        """Replace known_guilds with the current guild list. No invite
        links here (unlike /server) - this fires on every join/leave, so
        generating an invite each time would be wasteful and spammy."""
        db.connection.execute("DELETE FROM known_guilds")
        for g in self.bot.guilds:
            db.connection.execute(
                "INSERT INTO known_guilds (guild_id, name, member_count, invite) VALUES (?, ?, ?, NULL)",
                (str(g.id), g.name, g.member_count)
            )
        db.connection.commit()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.update_server_list()

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
        self.update_server_list()

async def setup(bot):
    await bot.add_cog(ServerNotify(bot))
