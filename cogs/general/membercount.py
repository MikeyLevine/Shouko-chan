import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os

class MemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_ids = self.load_channel_ids()
        self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

    def load_channel_ids(self):
        if os.path.exists("channel_ids.json"):
            with open("channel_ids.json", "r") as f:
                return json.load(f)
        return {}

    def save_channel_ids(self):
        with open("channel_ids.json", "w") as f:
            json.dump(self.channel_ids, f)

    @tasks.loop(minutes=5)
    async def update_stats(self):
        for guild in self.bot.guilds:
            stats_channels = {
                "Members:": f"Members: {guild.member_count}",
                "Bots:": f"Bots: {sum(1 for member in guild.members if member.bot)}",
                "Channels:": f"Channels: {len(guild.channels)}",
                "Created:": f"Created: {guild.created_at.strftime('%Y-%m-%d')}"
            }

            for stat_name, stat_value in stats_channels.items():
                channel_id = self.channel_ids.get(f"{guild.id}_{stat_name}")
                if channel_id:
                    channel = guild.get_channel(channel_id)
                    if channel:
                        await channel.edit(name=stat_value)
                    else:
                        new_channel = await guild.create_voice_channel(stat_value)
                        self.channel_ids[f"{guild.id}_{stat_name}"] = new_channel.id
                        # Set permissions to make the channel visible but not joinable for everyone except the bot
                        overwrite = {
                            guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
                            guild.me: discord.PermissionOverwrite(view_channel=True, connect=True)
                        }
                        await new_channel.edit(overwrites=overwrite)
                else:
                    new_channel = await guild.create_voice_channel(stat_value)
                    self.channel_ids[f"{guild.id}_{stat_name}"] = new_channel.id
                    # Set permissions to make the channel visible but not joinable for everyone except the bot
                    overwrite = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
                        guild.me: discord.PermissionOverwrite(view_channel=True, connect=True)
                    }
                    await new_channel.edit(overwrites=overwrite)

        self.save_channel_ids()

    @app_commands.command(name="membercount", description="Display server statistics")
    @app_commands.checks.has_permissions(administrator=True)
    async def membercount(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="Select Statistics",
                description="Please select the statistics you want to display:",
                color=discord.Color.blue()
            )

            options = [
                discord.SelectOption(label="Member Count", description="Total number of members"),
                discord.SelectOption(label="Bot Count", description="Total number of bots"),
                discord.SelectOption(label="Channels Count", description="Total number of channels"),
                discord.SelectOption(label="Server Creation Date", description="Date when the server was created")
            ]

            select = discord.ui.Select(placeholder="Choose statistics...", options=options, max_values=len(options))

            async def select_callback(interaction: discord.Interaction):
                try:
                    guild = interaction.guild
                    messages = []
                    for value in select.values:
                        if value == "Member Count":
                            count = guild.member_count
                            messages.append(f"Total members: {count}")
                        elif value == "Bot Count":
                            count = sum(1 for member in guild.members if member.bot)
                            messages.append(f"Total bots: {count}")
                        elif value == "Channels Count":
                            count = len(guild.channels)
                            messages.append(f"Total channels: {count}")
                        elif value == "Server Creation Date":
                            creation_date = guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            messages.append(f"Server creation date: {creation_date}")

                    # Create a new embed with the selected statistics
                    result_embed = discord.Embed(
                        title="Selected Statistics",
                        description="\n".join(messages),
                        color=discord.Color.green()
                    )

                    # Add a button to create the channels
                    done_button = discord.ui.Button(label="Create", style=discord.ButtonStyle.primary)

                    async def done_callback(interaction: discord.Interaction):
                        try:
                            # Find or create the "Server Stats" category
                            category = discord.utils.get(guild.categories, name="Server Stats")
                            if not category:
                                category = await guild.create_category("Server Stats", position=0)
                            else:
                                await category.edit(position=0)

                            # Create locked voice channels under the "Server Stats" category
                            for message in messages:
                                channel_name = message.split(":")[0]
                                channel_value = message.split(":")[1].strip()
                                new_channel = await guild.create_voice_channel(
                                    name=f"{channel_name}: {channel_value}",
                                    category=category
                                )
                                # Set permissions to make the channel visible but not joinable for everyone except the bot
                                overwrite = {
                                    guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
                                    guild.me: discord.PermissionOverwrite(view_channel=True, connect=True)
                                }
                                await new_channel.edit(overwrites=overwrite)

                            await interaction.response.edit_message(embed=result_embed, view=None)
                        except Exception as e:
                            await interaction.response.send_message(f"An error occurred in done_callback: {e}", ephemeral=True)

                    done_button.callback = done_callback

                    view = discord.ui.View()
                    view.add_item(done_button)

                    await interaction.response.send_message(embed=result_embed, view=view, ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"An error occurred in select_callback: {e}", ephemeral=True)

            select.callback = select_callback

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MemberCount(bot))