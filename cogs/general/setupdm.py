import discord
from discord.ext import commands
from discord import app_commands
import json
import os

OWNER_ID = 1255466299258306611  # Replace with your Discord user ID

class SetupDM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dm_channel_id = self.load_dm_channel_id()

    def is_owner(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID

    def load_dm_channel_id(self):
        if os.path.exists("dm_channel.json"):
            with open("dm_channel.json", "r") as f:
                data = json.load(f)
                return data.get("dm_channel_id")
        return None

    def save_dm_channel_id(self):
        with open("dm_channel.json", "w") as f:
            json.dump({"dm_channel_id": self.dm_channel_id}, f)

    @app_commands.command(name="setupdm", description="Set up a channel to receive DMs")
    @app_commands.check(is_owner)
    async def setupdm(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="Setup DM Channel",
                description="Please select a channel to receive DMs:",
                color=discord.Color.blue()
            )

            channels = [
                discord.SelectOption(label=channel.name, value=str(channel.id))
                for channel in interaction.guild.text_channels
            ]

            # Split channels into chunks of 25
            chunks = [channels[i:i + 25] for i in range(0, len(channels), 25)]

            view = discord.ui.View()

            for chunk in chunks:
                select = discord.ui.Select(placeholder="Choose a channel...", options=chunk)

                async def select_callback(interaction: discord.Interaction):
                    self.dm_channel_id = int(select.values[0])
                    self.save_dm_channel_id()
                    await interaction.response.send_message(f"DMs will be sent to <#{self.dm_channel_id}>", ephemeral=True)

                select.callback = select_callback
                view.add_item(select)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if isinstance(message.channel, discord.DMChannel):
            if self.dm_channel_id:
                channel = self.bot.get_channel(self.dm_channel_id)
                if channel:
                    embed = discord.Embed(
                        title="New DM Received",
                        description=f"From: {message.author} ({message.author.id})\n\n{message.content}",
                        color=discord.Color.green()
                    )
                    await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SetupDM(bot))