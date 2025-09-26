import discord
from discord.ext import commands
from discord import app_commands
import json
import os

CONFIG_FILE = "data/inandout_config.json"

class InAndOut(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_configs = self.load_configs()
        print("[DEBUG] InAndOut cog loaded")  # debug on cog load

    def load_configs(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_configs(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.guild_configs, f, indent=4)

    def get_guild_config(self, guild_id):
        return self.guild_configs.get(str(guild_id), {})

    def set_guild_config(self, guild_id, welcome, goodbye, channel_id, welcome_image=None, goodbye_image=None):
        self.guild_configs[str(guild_id)] = {
            "welcome_message": welcome,
            "goodbye_message": goodbye,
            "announcement_channel_id": channel_id,
            "welcome_image": welcome_image,
            "goodbye_image": goodbye_image
        }
        self.save_configs()

    @app_commands.command(
        name="setup",
        description="Set welcome/goodbye messages, announcement channel, and optional images"
    )
    @app_commands.describe(
        welcome_message="The welcome message (use {member} for mention)",
        goodbye_message="The goodbye message (use {member} for mention)",
        channel="The announcement channel",
        welcome_image="Optional: URL of a welcome image or GIF",
        goodbye_image="Optional: URL of a goodbye image or GIF"
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        welcome_message: str,
        goodbye_message: str,
        channel: discord.TextChannel,
        welcome_image: str = None,
        goodbye_image: str = None
    ):
        try:
            guild_id = interaction.guild.id
            self.set_guild_config(guild_id, welcome_message, goodbye_message, channel.id, welcome_image, goodbye_image)
            print(f"[DEBUG] Setup invoked for guild {guild_id} by {interaction.user}")
            embed = discord.Embed(
                title="Setup Complete",
                description=f"✅ Welcome message: {welcome_message}\n✅ Goodbye message: {goodbye_message}\n✅ Announcement channel: {channel.mention}",
                color=discord.Color.red()
            )
            if welcome_image:
                embed.set_image(url=welcome_image)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"[ERROR] Setup command error: {e}")
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = member.guild.id
        config = self.get_guild_config(guild_id)
        welcome_msg = config.get("welcome_message")
        channel_id = config.get("announcement_channel_id")
        welcome_image = config.get("welcome_image")
        print(f"[DEBUG] Member joined: {member.name} in guild {guild_id}")
        if welcome_msg and channel_id:
            channel = member.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(description=welcome_msg.format(member=member.mention), color=discord.Color.green())
                if welcome_image:
                    embed.set_image(url=welcome_image)
                await channel.send(embed=embed)
            else:
                print("[DEBUG] Announcement channel not found")
        else:
            print("[DEBUG] Guild config missing or incomplete")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild_id = member.guild.id
        config = self.get_guild_config(guild_id)
        goodbye_msg = config.get("goodbye_message")
        channel_id = config.get("announcement_channel_id")
        goodbye_image = config.get("goodbye_image")
        print(f"[DEBUG] Member left: {member.name} in guild {guild_id}")
        if goodbye_msg and channel_id:
            channel = member.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(description=goodbye_msg.format(member=member.mention), color=discord.Color.red())
                if goodbye_image:
                    embed.set_image(url=goodbye_image)
                await channel.send(embed=embed)
            else:
                print("[DEBUG] Announcement channel not found")
        else:
            print("[DEBUG] Guild config missing or incomplete")

async def setup(bot):
    await bot.add_cog(InAndOut(bot))
