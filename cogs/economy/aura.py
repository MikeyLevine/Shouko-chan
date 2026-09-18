import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
import random

STARTING_BALANCE = 500
MIN_EARN = 5
MAX_EARN = 15
DEFAULT_COOLDOWN = 8 * 60


class Aura(commands.Cog):
    """Per-server currency system. Other cogs (blackjack, slots, ...) read
    and write balances through bot.get_cog("Aura")'s helper methods rather
    than touching the data file directly."""

    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/aura.json"
        self.server_settings_file = "data/server_settings.json"
        self.balances = self.load_data()  # {guild_id: {user_id: int}}
        self.last_earn_time = {}  # {(guild_id, user_id): timestamp}
        print("[DEBUG] Aura cog loaded")  # Debug output

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                return json.load(f)
        return {}

    def save_data(self):
        with open(self.data_file, "w") as f:
            json.dump(self.balances, f, indent=4)

    def _cooldown_for(self, guild_id):
        # Reuses the same per-server chat cooldown set by /set_cooldown for
        # leveling, so one setting governs the "how often does chatting pay
        # out" cadence for both XP and Aura.
        if os.path.exists(self.server_settings_file):
            with open(self.server_settings_file, "r") as f:
                settings = json.load(f)
            return settings.get(str(guild_id), {}).get("cooldown_time", DEFAULT_COOLDOWN)
        return DEFAULT_COOLDOWN

    def ensure_account(self, guild_id, user_id):
        guild_data = self.balances.setdefault(str(guild_id), {})
        if str(user_id) not in guild_data:
            guild_data[str(user_id)] = STARTING_BALANCE
        return guild_data[str(user_id)]

    def get_balance(self, guild_id, user_id):
        return self.ensure_account(guild_id, user_id)

    def add_balance(self, guild_id, user_id, amount):
        self.ensure_account(guild_id, user_id)
        self.balances[str(guild_id)][str(user_id)] += amount
        self.save_data()
        return self.balances[str(guild_id)][str(user_id)]

    def remove_balance(self, guild_id, user_id, amount):
        """Returns False (and leaves the balance untouched) if funds are
        insufficient, True if the amount was deducted."""
        balance = self.ensure_account(guild_id, user_id)
        if balance < amount:
            return False
        self.balances[str(guild_id)][str(user_id)] -= amount
        self.save_data()
        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        current_time = time.time()

        key = (guild_id, user_id)
        last_time = self.last_earn_time.get(key)
        if last_time is not None and current_time - last_time < self._cooldown_for(guild_id):
            return

        self.add_balance(guild_id, user_id, random.randint(MIN_EARN, MAX_EARN))
        self.last_earn_time[key] = current_time

    @app_commands.command(name="balance", description="Check your Aura balance in this server")
    @app_commands.describe(member="Check someone else's balance instead of your own")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        target = member or interaction.user
        bal = self.get_balance(interaction.guild.id, target.id)
        embed = discord.Embed(
            title="Aura Balance",
            description=f"{target.mention} has **{bal}** Aura in **{interaction.guild.name}**.",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Aura(bot))
