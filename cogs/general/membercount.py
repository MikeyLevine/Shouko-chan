import discord
from discord.ext import commands, tasks
from discord import app_commands

class MemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

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
                # Find existing channel or create a new one
                channel = discord.utils.get(guild.channels, name__startswith=stat_name)
                if channel:
                    await channel.edit(name=stat_value)
                else:
                    channel = await guild.create_text_channel(stat_value)

                # Set permissions to make the channel read-only for everyone except the bot
                overwrite = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False),
                    guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                await channel.edit(overwrites=overwrite)

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

                # Add a text input for the goal number
                goal_input = discord.ui.TextInput(
                    label="Enter the goal number:",
                    placeholder="e.g., 1000",
                    style=discord.TextStyle.short
                )

                # Add a button to submit the goal number
                done_button = discord.ui.Button(label="Done", style=discord.ButtonStyle.primary)

                async def done_callback(interaction: discord.Interaction):
                    goal_number = goal_input.value
                    result_embed.add_field(name="Goal", value=f"🏆 {goal_number}", inline=False)
                    await interaction.response.edit_message(embed=result_embed, view=None)

                done_button.callback = done_callback

                view = discord.ui.View()
                view.add_item(goal_input)
                view.add_item(done_button)

                await interaction.response.send_message(embed=result_embed, view=view, ephemeral=True)

            select.callback = select_callback

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MemberCount(bot))