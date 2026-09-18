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

DAILY_COOLDOWN = 24 * 60 * 60
DAILY_STREAK_GRACE = 48 * 60 * 60  # miss more than this and the streak resets
DAILY_MIN = 100
DAILY_MAX = 200
DAILY_STREAK_BONUS_PER_DAY = 10
DAILY_STREAK_BONUS_CAP = 100

SCAVENGE_COOLDOWN = 30 * 60
SCAVENGE_MIN = 1
SCAVENGE_MAX = 50
SCAVENGE_NOTHING_CHANCE = 0.2
SCAVENGE_FLAVOR = [
    "You check under the couch cushions and find {amount} Aura.",
    "You dig through your pockets and find {amount} Aura.",
    "A stranger drops {amount} Aura and doesn't notice.",
    "You find {amount} Aura on the sidewalk.",
    "You scavenge a vending machine's coin return for {amount} Aura.",
    "You find {amount} Aura in an old jacket pocket.",
]
SCAVENGE_NOTHING_FLAVOR = [
    "You check your pockets... nothing but lint.",
    "You search high and low and come up empty.",
    "Nothing but dust bunnies here.",
    "You find a gum wrapper. Not exactly currency.",
]


class Aura(commands.Cog):
    """Per-server currency system. Other cogs (blackjack, slots, ...) read
    and write balances through bot.get_cog("Aura")'s helper methods rather
    than touching the data file directly."""

    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/aura.json"
        self.server_settings_file = "data/server_settings.json"
        self.balances = self.load_data()  # {guild_id: {user_id: {"balance", "last_daily", "daily_streak", "last_scavenge"}}}
        self.last_earn_time = {}  # passive chat-earning cooldown tracker, in-memory only
        print("[DEBUG] Aura cog loaded")  # Debug output

    def load_data(self):
        if not os.path.exists(self.data_file):
            return {}
        with open(self.data_file, "r") as f:
            data = json.load(f)

        migrated = False
        for guild_data in data.values():
            for user_id, value in guild_data.items():
                if isinstance(value, int):
                    guild_data[user_id] = self._new_account(value)
                    migrated = True
        if migrated:
            print("[DEBUG] Migrated aura.json balances to the per-user dict format (added daily/scavenge tracking)")
        return data

    def save_data(self):
        with open(self.data_file, "w") as f:
            json.dump(self.balances, f, indent=4)

    @staticmethod
    def _new_account(balance=STARTING_BALANCE):
        return {"balance": balance, "last_daily": None, "daily_streak": 0, "last_scavenge": None}

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
            guild_data[str(user_id)] = self._new_account()
        return guild_data[str(user_id)]

    def get_balance(self, guild_id, user_id):
        return self.ensure_account(guild_id, user_id)["balance"]

    def add_balance(self, guild_id, user_id, amount):
        entry = self.ensure_account(guild_id, user_id)
        entry["balance"] += amount
        self.save_data()
        return entry["balance"]

    def remove_balance(self, guild_id, user_id, amount):
        """Returns False (and leaves the balance untouched) if funds are
        insufficient, True if the amount was deducted."""
        entry = self.ensure_account(guild_id, user_id)
        if entry["balance"] < amount:
            return False
        entry["balance"] -= amount
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

    @app_commands.command(name="daily", description="Claim your daily Aura")
    async def daily(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        entry = self.ensure_account(interaction.guild.id, interaction.user.id)
        now = time.time()
        last_daily = entry.get("last_daily")

        if last_daily is not None:
            elapsed = now - last_daily
            if elapsed < DAILY_COOLDOWN:
                remaining = int(DAILY_COOLDOWN - elapsed)
                hours, minutes = remaining // 3600, (remaining % 3600) // 60
                await interaction.response.send_message(
                    f"⏳ You already claimed your daily Aura. Try again in **{hours}h {minutes}m**.",
                    ephemeral=True
                )
                return
            if elapsed > DAILY_STREAK_GRACE:
                entry["daily_streak"] = 0

        entry["daily_streak"] = entry.get("daily_streak", 0) + 1
        streak = entry["daily_streak"]
        bonus = min((streak - 1) * DAILY_STREAK_BONUS_PER_DAY, DAILY_STREAK_BONUS_CAP)
        base = random.randint(DAILY_MIN, DAILY_MAX)
        total = base + bonus

        entry["balance"] += total
        entry["last_daily"] = now
        self.save_data()

        embed = discord.Embed(
            title="💰 Daily Aura Claimed",
            description=(
                f"You claimed **{total}** Aura ({base} base + {bonus} streak bonus).\n"
                f"🔥 Streak: **{streak}** day{'s' if streak != 1 else ''}\n"
                f"Balance: **{entry['balance']}** Aura"
            ),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="scavenge", description="Scavenge for spare change")
    async def scavenge(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        entry = self.ensure_account(interaction.guild.id, interaction.user.id)
        now = time.time()
        last_scavenge = entry.get("last_scavenge")

        if last_scavenge is not None and now - last_scavenge < SCAVENGE_COOLDOWN:
            minutes = int(SCAVENGE_COOLDOWN - (now - last_scavenge)) // 60 + 1
            await interaction.response.send_message(
                f"⏳ You already scavenged recently. Try again in **{minutes}m**.",
                ephemeral=True
            )
            return

        entry["last_scavenge"] = now

        if random.random() < SCAVENGE_NOTHING_CHANCE:
            self.save_data()
            embed = discord.Embed(
                title="🔍 Scavenge",
                description=random.choice(SCAVENGE_NOTHING_FLAVOR),
                color=discord.Color.dark_grey()
            )
            await interaction.response.send_message(embed=embed)
            return

        amount = random.randint(SCAVENGE_MIN, SCAVENGE_MAX)
        entry["balance"] += amount
        self.save_data()

        flavor = random.choice(SCAVENGE_FLAVOR).format(amount=amount)
        embed = discord.Embed(
            title="🔍 Scavenge",
            description=f"{flavor}\nBalance: **{entry['balance']}** Aura",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Aura(bot))
