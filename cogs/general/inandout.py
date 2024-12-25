import discord
from discord.ext import commands
from discord import app_commands

class InAndOut(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_message = "Welcome to the server, {member}!"
        self.goodbye_message = "Goodbye, {member}. We will miss you!"
        self.announcement_channel = None

    @app_commands.command(name="setup", description="Set the welcome and goodbye messages and announcement channel")
    async def setup(self, interaction: discord.Interaction, welcome_message: str, goodbye_message: str, channel: discord.TextChannel):
        try:
            print("Setup command invoked")  # Debug print
            self.welcome_message = welcome_message
            self.goodbye_message = goodbye_message
            self.announcement_channel = channel
            print(f"New welcome message set: {welcome_message}")
            print(f"New goodbye message set: {goodbye_message}")
            print(f"Announcement channel set to: {channel.name}")
            embed = discord.Embed(
                title="Setup Complete",
                description=f"Welcome message set to: {welcome_message}\nGoodbye message set to: {goodbye_message}\nAnnouncement channel set to: {channel.mention}",
                color=discord.Color.red()  # Light red color
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"Error in setup command: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        print(f"Member joined: {member.name}")  # Debug print
        if self.announcement_channel:
            await self.announcement_channel.send(self.welcome_message.format(member=member.mention))
        else:
            print("Announcement channel not set")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        print(f"Member left: {member.name}")  # Debug print
        if self.announcement_channel:
            await self.announcement_channel.send(self.goodbye_message.format(member=member.mention))
        else:
            print("Announcement channel not set")

async def setup(bot):
    await bot.add_cog(InAndOut(bot))
