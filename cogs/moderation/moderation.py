import discord
from discord.ext import commands
from discord import app_commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Moderation cog loaded")

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="Member Kicked",
                description=f"{member.mention} was kicked.\nReason: {reason}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            print(f"[DEBUG] {interaction.user} kicked {member} | Reason: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"Error kicking member: {e}", ephemeral=True)
            print(f"[ERROR] Kick command failed: {e}")

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        try:
            await member.ban(reason=reason)
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member.mention} was banned.\nReason: {reason}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            print(f"[DEBUG] {interaction.user} banned {member} | Reason: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"Error banning member: {e}", ephemeral=True)
            print(f"[ERROR] Ban command failed: {e}")

    @app_commands.command(name="clear", description="Clear messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        try:
            await interaction.response.defer(ephemeral=True)
            deleted = await interaction.channel.purge(limit=amount)
            embed = discord.Embed(
                title="Messages Cleared",
                description=f"Deleted {len(deleted)} messages.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"[DEBUG] {interaction.user} cleared {len(deleted)} messages in {interaction.channel}")
        except Exception as e:
            await interaction.followup.send(f"Error clearing messages: {e}", ephemeral=True)
            print(f"[ERROR] Clear command failed: {e}")

    @app_commands.command(name="mute", description="Mute a member")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        try:
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await interaction.guild.create_role(name="Muted")
                for channel in interaction.guild.channels:
                    await channel.set_permissions(mute_role, speak=False, send_messages=False, read_message_history=True, read_messages=False)
            await member.add_roles(mute_role, reason=reason)
            embed = discord.Embed(
                title="Member Muted",
                description=f"{member.mention} was muted.\nReason: {reason}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            print(f"[DEBUG] {interaction.user} muted {member} | Reason: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"Error muting member: {e}", ephemeral=True)
            print(f"[ERROR] Mute command failed: {e}")

    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        try:
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if mute_role and mute_role in member.roles:
                await member.remove_roles(mute_role, reason=reason)
                embed = discord.Embed(
                    title="Member Unmuted",
                    description=f"{member.mention} was unmuted.\nReason: {reason}",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
                print(f"[DEBUG] {interaction.user} unmuted {member} | Reason: {reason}")
            else:
                await interaction.response.send_message(f"{member.mention} is not muted.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error unmuting member: {e}", ephemeral=True)
            print(f"[ERROR] Unmute command failed: {e}")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
