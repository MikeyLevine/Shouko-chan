import discord
from discord.ext import commands
from discord import app_commands
import json

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = None
        self.load_log_channel()
        print("Logging cog initialized")  # Debug print

    def load_log_channel(self):
        try:
            with open('log_channel.json', 'r') as f:
                data = json.load(f)
                self.log_channel_id = data.get('log_channel_id')
        except FileNotFoundError:
            pass

    def save_log_channel(self, channel_id):
        with open('log_channel.json', 'w') as f:
            json.dump({'log_channel_id': channel_id}, f)
        self.log_channel_id = channel_id

    @app_commands.command(name="log", description="Set the channel for logging deleted and edited messages.")
    @app_commands.checks.has_permissions(administrator=True)
    async def log(self, interaction: discord.Interaction):
        class ChannelSelect(discord.ui.Select):
            def __init__(self, cog):
                self.cog = cog
                options = [
                    discord.SelectOption(label=channel.name, value=str(channel.id))
                    for channel in interaction.guild.text_channels
                ]
                super().__init__(placeholder="Select a channel for logs", options=options)

            async def callback(self, interaction: discord.Interaction):
                selected_channel_id = int(self.values[0])
                self.cog.save_log_channel(selected_channel_id)
                selected_channel = self.cog.bot.get_channel(selected_channel_id)
                await interaction.response.send_message(f"Logs will be sent to {selected_channel.mention}", ephemeral=True)

        class ChannelSelectView(discord.ui.View):
            def __init__(self, cog):
                super().__init__()
                self.add_item(ChannelSelect(cog))

        await interaction.response.send_message("Please select a channel for logs:", view=ChannelSelectView(self), ephemeral=True)
        print("Log command registered")  # Debug print

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if self.log_channel_id:
            log_channel = self.bot.get_channel(self.log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="Message Deleted",
                    description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content}",
                    color=discord.Color.red()
                )
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if self.log_channel_id:
            log_channel = self.bot.get_channel(self.log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="Message Edited",
                    description=f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n**Before:** {before.content}\n**After:** {after.content}",
                    color=discord.Color.orange()
                )
                await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
    print("Logging cog setup complete")  # Debug print