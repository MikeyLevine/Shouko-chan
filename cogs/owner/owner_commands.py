import discord
from discord.ext import commands
from discord import app_commands

OWNER_ID = 1255466299258306611  # Replace with your Discord user ID

class OwnerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] OwnerCommands cog loaded")  # Debug output

    @staticmethod
    def is_owner(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID

    @app_commands.command(name="type", description="Send a message in a server channel")
    @app_commands.check(is_owner)
    async def type(self, interaction: discord.Interaction, channel_id: str, message: str):
        print(f"[DEBUG] type command invoked by {interaction.user} for channel {channel_id}")  # Debug
        try:
            channel_id = int(channel_id)
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(message)
                await interaction.response.send_message(f"Message sent to {channel.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("Channel not found. Please check the channel ID.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Channel ID must be an integer.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            print(f"[ERROR] type command error: {e}")

    @app_commands.command(name="dm", description="Send a direct message to a user")
    @app_commands.check(is_owner)
    async def dm(self, interaction: discord.Interaction, user_id: str, message: str):
        print(f"[DEBUG] dm command invoked by {interaction.user} for user {user_id}")  # Debug
        try:
            user_id = int(user_id)
            user = await self.bot.fetch_user(user_id)
            if user:
                await user.send(message)
                await interaction.response.send_message(f"Message sent to {user.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("User not found. Please check the user ID.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("User ID must be an integer.", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("User not found. Please check the user ID.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Cannot send message to this user. They might have DMs disabled.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            print(f"[ERROR] dm command error: {e}")

    @app_commands.command(name="grant", description="[Owner] Give (or remove) a user's Aura or XP in this server")
    @app_commands.check(is_owner)
    @app_commands.describe(member="Who to adjust", currency="Aura or XP", amount="Amount to give (negative to remove)")
    @app_commands.choices(currency=[
        app_commands.Choice(name="Aura", value="aura"),
        app_commands.Choice(name="XP", value="xp"),
    ])
    async def grant(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        currency: app_commands.Choice[str],
        amount: int,
    ):
        print(f"[DEBUG] grant command invoked by {interaction.user}: {amount} {currency.value} -> {member}")  # Debug
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        verb = "Gave" if amount >= 0 else "Removed"
        direction = "to" if amount >= 0 else "from"

        if currency.value == "aura":
            aura_cog = self.bot.get_cog("Aura")
            if not aura_cog:
                await interaction.response.send_message("⚠️ Aura system is not available right now.", ephemeral=True)
                return
            current = aura_cog.get_balance(interaction.guild.id, member.id)
            new_balance = aura_cog.set_balance(interaction.guild.id, member.id, current + amount)
            await interaction.response.send_message(
                f"✅ {verb} **{abs(amount)}** Aura {direction} {member.mention}. New balance: **{new_balance}**.",
                ephemeral=True
            )
        else:
            leveling_cog = self.bot.get_cog("Leveling")
            if not leveling_cog:
                await interaction.response.send_message("⚠️ Leveling system is not available right now.", ephemeral=True)
                return
            entry = leveling_cog.get_user_entry(interaction.guild.id, member.id)
            entry["exp"] = max(0, entry["exp"] + amount)
            entry["level"] = leveling_cog.calculate_level(entry["exp"])
            leveling_cog.save_user_data()
            await interaction.response.send_message(
                f"✅ {verb} **{abs(amount)}** XP {direction} {member.mention}. "
                f"New total: **{entry['exp']}** XP (Level {entry['level']}).",
                ephemeral=True
            )

    @type.error
    @dm.error
    @grant.error
    async def owner_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
            print(f"[ERROR] Owner command error: {error}")

async def setup(bot):
    await bot.add_cog(OwnerCommands(bot))
