import discord
from discord.ext import commands
from discord import app_commands

class MemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="membercount", description="Display server statistics")
    @app_commands.checks.has_permissions(administrator=True)
    async def membercount(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="Select a Statistic",
                description="Please select the statistic you want to display:",
                color=discord.Color.blue()
            )

            options = [
                discord.SelectOption(label="Member Count", description="Total number of members"),
                discord.SelectOption(label="Bot Count", description="Total number of bots"),
                discord.SelectOption(label="Channels Count", description="Total number of channels"),
                discord.SelectOption(label="Server Creation Date", description="Date when the server was created")
            ]

            select = discord.ui.Select(placeholder="Choose a statistic...", options=options)

            async def select_callback(interaction: discord.Interaction):
                guild = interaction.guild
                if select.values[0] == "Member Count":
                    count = guild.member_count
                    message = f"Total members: {count}"
                elif select.values[0] == "Bot Count":
                    count = sum(1 for member in guild.members if member.bot)
                    message = f"Total bots: {count}"
                elif select.values[0] == "Channels Count":
                    count = len(guild.channels)
                    message = f"Total channels: {count}"
                elif select.values[0] == "Server Creation Date":
                    creation_date = guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    message = f"Server creation date: {creation_date}"
                else:
                    message = "Invalid option."

                await interaction.response.send_message(message, ephemeral=True)

            select.callback = select_callback

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MemberCount(bot))