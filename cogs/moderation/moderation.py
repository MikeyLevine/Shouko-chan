import discord
from discord.ext import commands
from discord import app_commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server. Requires Kick Members permission.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        await member.kick(reason=reason)
        await interaction.response.send_message(f'Kicked {member.mention} for reason: {reason}', ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server. Requires Ban Members permission.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        await member.ban(reason=reason)
        await interaction.response.send_message(f'Banned {member.mention} for reason: {reason}', ephemeral=True)

    @app_commands.command(name="clear", description="Clear messages. Requires Manage Messages permission.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)  # Defer the response to give more time
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f'Cleared {len(deleted)} messages', ephemeral=True)

    @app_commands.command(name="mute", description="Mute a member. Requires Manage Roles permission.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await interaction.guild.create_role(name="Muted")
            for channel in interaction.guild.channels:
                await channel.set_permissions(mute_role, speak=False, send_messages=False, read_message_history=True, read_messages=False)
        await member.add_roles(mute_role, reason=reason)
        await interaction.response.send_message(f'Muted {member.mention} for reason: {reason}', ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))