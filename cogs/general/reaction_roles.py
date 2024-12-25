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

    @app_commands.command(name="create_role_message", description="Create a role message with reactions")
    async def create_role_message(self, interaction: discord.Interaction, title: str, description: str, roles: str, emojis: str):
        await interaction.response.defer(ephemeral=True)  # Acknowledge the interaction immediately

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()  # Light blue color
        )
        
        role_list = roles.split(',')
        emoji_list = emojis.split(',')
        
        if len(role_list) != len(emoji_list):
            await interaction.followup.send("The number of roles and emojis must be the same.", ephemeral=True)
            return
        
        for role, emoji in zip(role_list, emoji_list):
            role_name = role.strip()
            emoji_name = emoji.strip()
            embed.add_field(name=f"{emoji_name} {role_name}", value="\u200b", inline=False)
            self.reaction_roles[emoji_name] = role_name
        
        message = await interaction.channel.send(embed=embed)
        self.role_message_id = message.id
        self.save_data()
        
        for emoji in emoji_list:
            await message.add_reaction(emoji.strip())
        
        await interaction.followup.send("Role message created successfully.", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id != self.role_message_id:
            return
        
        if payload.user_id == self.bot.user.id:
            return  # Ignore reactions from the bot itself
        
        guild = self.bot.get_guild(payload.guild_id)
        role_name = self.reaction_roles.get(payload.emoji.name)
        
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                member = guild.get_member(payload.user_id)
                if member:
                    await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id != self.role_message_id:
            return
        
        if payload.user_id == self.bot.user.id:
            return  # Ignore reactions from the bot itself
        
        guild = self.bot.get_guild(payload.guild_id)
        role_name = self.reaction_roles.get(payload.emoji.name)
        
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                member = guild.get_member(payload.user_id)
                if member:
                    await member.remove_roles(role)

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))