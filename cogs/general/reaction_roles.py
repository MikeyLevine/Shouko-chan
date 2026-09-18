import discord
from discord.ext import commands
from discord import app_commands

import db

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] ReactionRoles cog loaded")  # Debug output

    def get_role_message_id(self):
        row = db.connection.execute("SELECT role_message_id FROM reaction_role_config WHERE id = 1").fetchone()
        return int(row["role_message_id"]) if row and row["role_message_id"] else None

    def get_reaction_roles(self):
        rows = db.connection.execute("SELECT emoji, role_id FROM reaction_role_mappings").fetchall()
        return {r["emoji"]: int(r["role_id"]) for r in rows}

    def set_role_message_id(self, message_id):
        db.connection.execute(
            "INSERT INTO reaction_role_config (id, role_message_id) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET role_message_id = excluded.role_message_id",
            (str(message_id),)
        )
        db.connection.commit()

    def replace_reaction_roles(self, mapping):
        db.connection.execute("DELETE FROM reaction_role_mappings")
        for emoji, role_id in mapping.items():
            db.connection.execute(
                "INSERT INTO reaction_role_mappings (emoji, role_id) VALUES (?, ?)", (emoji, str(role_id))
            )
        db.connection.commit()

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

            new_mapping = self.get_reaction_roles() if add else {}
            roles = roles.split(',')
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
                        new_mapping[str(partial_emoji)] = role_id
                    else:
                        await interaction.response.send_message(f"Role with ID {role_id} not found.", ephemeral=True)
                        return
                except ValueError:
                    await interaction.response.send_message("Invalid format. Use `emoji:role_id`.", ephemeral=True)
                    return

            self.replace_reaction_roles(new_mapping)
            self.set_role_message_id(message_id)

            embed = message.embeds[0] if add and message.embeds else discord.Embed(
                title=title or "",
                description=description or "",
                color=discord.Color.blue()
            )

            if title: embed.title = title
            if description: embed.description = description

            for emoji, role_id in new_mapping.items():
                guild_role = interaction.guild.get_role(role_id)
                if guild_role and not any(field.name == emoji for field in embed.fields):
                    embed.add_field(name=emoji, value=guild_role.name, inline=False)

            try:
                await message.edit(embed=embed)
            except discord.Forbidden:
                new_message = await interaction.channel.send(embed=embed)
                self.set_role_message_id(new_message.id)
                message = new_message

            for emoji in new_mapping.keys():
                await message.add_reaction(discord.PartialEmoji.from_str(emoji))

            await interaction.response.send_message("Reaction roles set up successfully.", ephemeral=True)
            print(f"[DEBUG] Reaction roles setup complete for message {message_id}")  # Debug
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            print(f"[ERROR] setupreactionroles error: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id != self.get_role_message_id():
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role_id = self.get_reaction_roles().get(str(payload.emoji))
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
        if payload.message_id != self.get_role_message_id():
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role_id = self.get_reaction_roles().get(str(payload.emoji))
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
