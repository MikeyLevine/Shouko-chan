import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help for all commands")
    async def help(self, interaction: discord.Interaction):
        try:
            excluded_commands = ['type', 'dm', 'setupdm', 'set_cooldown', 'toggle_leveling']
            commands_list = [cmd for cmd in self.bot.tree.walk_commands() if cmd.name not in excluded_commands]
            pages = [commands_list[i:i + 25] for i in range(0, len(commands_list), 25)]

            for page_number, page in enumerate(pages, start=1):
                embed = discord.Embed(
                    title=f"Help - Page {page_number}/{len(pages)}",
                    description="List of all available commands",
                    color=discord.Color.blue()
                )

                for command in page:
                    embed.add_field(
                        name=f"/{command.name}",
                        value=command.description or "No description provided",
                        inline=False
                    )

                await interaction.user.send(embed=embed)
                print(f"Help command executed successfully for page {page_number}.")

            await interaction.response.send_message("I've sent you a DM with the list of commands.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I couldn't send you a DM. Please check your DM settings.", ephemeral=True)
        except Exception as e:
            print(f"Error executing help command: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))