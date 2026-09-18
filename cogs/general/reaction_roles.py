import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/reaction_roles.json'
        self.role_message_id = None
        self.reaction_roles = {}
        self.load_data()
        print("[DEBUG] ReactionRoles cog loaded")  # Debug output

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.role_message_id = data.get('role_message_id')
                self.reaction_roles = data.get('reaction_roles', {})
            print(f"[DEBUG] Loaded reaction roles data: {self.reaction_roles}")  # Debug

    def save_data(self):
        data = {
            'role_message_id': self.role_message_id,
            'reaction_roles': self.reaction_roles
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f)
        print(f"[DEBUG] Saved reaction roles data: {self.reaction_roles}")  # Debug

    @app_commands.command(name="setupreactionroles", description="Set up or add to reaction roles")
    @app_commands.checks.has_permissions(administrator=True)
    async def setupreactionroles(self, interaction: discord.Interaction, message_id: str, roles: str, title: str = None, description: str = None, add: bool = False):
        print(f"[DEBUG] setupreactionroles invoked by {interaction.user}")  # Debug
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
                    # rsplit on the LAST colon only - a custom emoji like
                    # <:pepe:123456789012345678> already contains colons of
                    # its own, so splitting on every colon breaks it.
                    emoji_str, role_id = role.rsplit(':', 1)
                    role_id = int(role_id.strip())
                    guild_role = interaction.guild.get_role(role_id)
                    if guild_role:
                        # Normalize through PartialEmoji so custom emoji are
                        # stored/reacted-with in the exact form discord.py
                        # expects, matching what on_raw_reaction_add sees.
                        partial_emoji = discord.PartialEmoji.from_str(emoji_str.strip())
                        self.reaction_roles[str(partial_emoji)] = role_id
                    else:
                        await interaction.response.send_message(f"Role with ID {role_id} not found.", ephemeral=True)
                        return
                except ValueError:
                    await interaction.response.send_message("Invalid format. Use `emoji:role_id`.", ephemeral=True)
                    return

            self.role_message_id = message_id
            self.save_data()

            embed = message.embeds[0] if add and message.embeds else discord.Embed(
                title=title or "",
                description=description or "",
                color=discord.Color.blue()
            )

            if title: embed.title = title
            if description: embed.description = description

            for emoji, role_id in self.reaction_roles.items():
                guild_role = interaction.guild.get_role(role_id)
                if guild_role and not any(field.name == emoji for field in embed.fields):
                    embed.add_field(name=emoji, value=guild_role.name, inline=False)

            try:
                await message.edit(embed=embed)
            except discord.Forbidden:
                new_message = await interaction.channel.send(embed=embed)
                self.role_message_id = new_message.id
                self.save_data()
                message = new_message

            for emoji in self.reaction_roles.keys():
                await message.add_reaction(discord.PartialEmoji.from_str(emoji))

            await interaction.response.send_message("Reaction roles set up successfully.", ephemeral=True)
            print(f"[DEBUG] Reaction roles setup complete for message {self.role_message_id}")  # Debug
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            print(f"[ERROR] setupreactionroles error: {e}")

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
        print(f"[DEBUG] Added role {role.name} to {member}")  # Debug

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
        print(f"[DEBUG] Removed role {role.name} from {member}")  # Debug

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
