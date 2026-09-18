import discord
from discord.ext import commands, tasks
from discord import app_commands

import db

class MemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_stats.start()
        print("[DEBUG] MemberCount cog loaded")

    def cog_unload(self):
        self.update_stats.cancel()

    def get_channel_id(self, guild_id, stat_name):
        row = db.connection.execute(
            "SELECT channel_id FROM stat_channels WHERE guild_id = ? AND stat_name = ?",
            (str(guild_id), stat_name)
        ).fetchone()
        return int(row["channel_id"]) if row else None

    def set_channel_id(self, guild_id, stat_name, channel_id):
        db.connection.execute(
            "INSERT INTO stat_channels (guild_id, stat_name, channel_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, stat_name) DO UPDATE SET channel_id = excluded.channel_id",
            (str(guild_id), stat_name, str(channel_id))
        )
        db.connection.commit()

    @tasks.loop(minutes=5)
    async def update_stats(self):
        """Update existing stats channels only. Do not create new ones."""
        for guild in self.bot.guilds:
            stats = {
                "Members": guild.member_count,
                "Bots": sum(1 for m in guild.members if m.bot),
                "Channels": len(guild.channels),
                "Created": guild.created_at.strftime("%Y-%m-%d")
            }

            for stat_name, stat_value in stats.items():
                channel_id = self.get_channel_id(guild.id, stat_name)
                if channel_id:
                    channel = guild.get_channel(channel_id)
                    if channel:
                        new_name = f"{stat_name}: {stat_value}"
                        if channel.name != new_name:
                            await channel.edit(name=new_name)
                # Do not create new channels automatically

    @app_commands.command(name="membercount", description="Create or update server statistics channels")
    @app_commands.checks.has_permissions(administrator=True)
    async def membercount(self, interaction: discord.Interaction):
        try:
            # Acknowledge immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)

            guild = interaction.guild
            # Find or create the "Server Stats" category
            category = discord.utils.get(guild.categories, name="Server Stats")
            if not category:
                category = await guild.create_category("Server Stats", position=0)

            stats = {
                "Members": guild.member_count,
                "Bots": sum(1 for m in guild.members if m.bot),
                "Channels": len(guild.channels),
                "Created": guild.created_at.strftime("%Y-%m-%d")
            }

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, connect=True)
            }

            # Create or update the channels manually
            for stat_name, stat_value in stats.items():
                channel_name = f"{stat_name}: {stat_value}"
                existing_id = self.get_channel_id(guild.id, stat_name)

                if existing_id:
                    channel = guild.get_channel(existing_id)
                    if channel:
                        if channel.name != channel_name:
                            await channel.edit(name=channel_name)
                        continue  # Already exists, updated
                # Create new channel
                new_channel = await guild.create_voice_channel(channel_name, category=category, overwrites=overwrites)
                self.set_channel_id(guild.id, stat_name, new_channel.id)

            await interaction.followup.send("Server statistics channels created/updated.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MemberCount(bot))
