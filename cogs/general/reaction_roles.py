import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'reaction_roles.json'
        self.role_message_id = None
        self.reaction_roles = {}
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.role_message_id = data.get('role_message_id')
                self.reaction_roles = data.get('reaction_roles', {})

    def save_data(self):
        data = {
            'role_message_id': self.role_message_id,
            'reaction_roles': self.reaction_roles
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f)

    @app_commands.command(name="setupreactionroles", description="Set up or add to reaction roles")
    @app_commands.checks.has_permissions(administrator=True)
    async def setupreactionroles(self, interaction: discord.Interaction, message_id: str, roles: str, title: str = None, description: str = None, add: bool = False):
        try:
            message_id = int(message_id)
            message = await interaction.channel.fetch_message(message_id)
            if not message:
                await interaction.response.send_message("Message not found. Please check the message ID.", ephemeral=True)
                return

            roles = roles.split(',')
            if not add:
                self.reaction_roles = {}
            for role in roles:
                try:
                    emoji, role_id = role.split(':')
                    role_id = int(role_id.strip())
                    role = interaction.guild.get_role(role_id)
                    if role:
                        self.reaction_roles[emoji.strip()] = role_id
                    else:
                        await interaction.response.send_message(f"Role with ID {role_id} not found.", ephemeral=True)
                        return
                except ValueError:
                    await interaction.response.send_message("Invalid format. Please use the format `emoji:role_id`.", ephemeral=True)
                    return

            self.role_message_id = message_id
            self.save_data()

            if not add:
                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=discord.Color.blue()
                )
            else:
                embed = message.embeds[0]
                if title:
                    embed.title = title
                if description:
                    embed.description = description

            for emoji, role_id in self.reaction_roles.items():
                role = interaction.guild.get_role(role_id)
                if role and not any(field.name == emoji for field in embed.fields):
                    embed.add_field(name=emoji, value=role.name, inline=False)

            try:
                await message.edit(embed=embed)
            except discord.Forbidden:
                new_message = await interaction.channel.send(embed=embed)
                self.role_message_id = new_message.id
                self.save_data()
                message = new_message

            # Add reactions to the message
            for emoji in self.reaction_roles.keys():
                await message.add_reaction(emoji)

            await interaction.response.send_message("Reaction roles set up successfully.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id != self.role_message_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role_id = self.reaction_roles.get(str(payload.emoji))
        if not role_id:
            return

        role = guild.get_role(role_id)
        if not role:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id != self.role_message_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role_id = self.reaction_roles.get(str(payload.emoji))
        if not role_id:
            return

        role = guild.get_role(role_id)
        if not role:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        await member.remove_roles(role)

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))