import discord
from discord.ext import commands
from discord import app_commands
import time
import random

import db
from cogs.profile.card import generate_leaderboard_card

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
    than touching the database directly."""

    def __init__(self, bot):
        self.bot = bot
        self.last_earn_time = {}  # passive chat-earning cooldown tracker, in-memory only
        print("[DEBUG] Aura cog loaded")  # Debug output

    def _cooldown_for(self, guild_id):
        # Reuses the same per-server chat cooldown set by /set_cooldown for
        # leveling, so one setting governs the "how often does chatting pay
        # out" cadence for both XP and Aura.
        row = db.connection.execute(
            "SELECT cooldown_time FROM server_settings WHERE guild_id = ?", (str(guild_id),)
        ).fetchone()
        return row["cooldown_time"] if row else DEFAULT_COOLDOWN

    def ensure_account(self, guild_id, user_id):
        guild_id, user_id = str(guild_id), str(user_id)
        row = db.connection.execute(
            "SELECT * FROM aura_accounts WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ).fetchone()
        if row is None:
            db.connection.execute(
                "INSERT INTO aura_accounts (guild_id, user_id, balance) VALUES (?, ?, ?)",
                (guild_id, user_id, STARTING_BALANCE)
            )
            db.connection.commit()
            row = db.connection.execute(
                "SELECT * FROM aura_accounts WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
            ).fetchone()
        return row

    def get_balance(self, guild_id, user_id):
        return self.ensure_account(guild_id, user_id)["balance"]

    def add_balance(self, guild_id, user_id, amount):
        self.ensure_account(guild_id, user_id)
        db.connection.execute(
            "UPDATE aura_accounts SET balance = balance + ? WHERE guild_id = ? AND user_id = ?",
            (amount, str(guild_id), str(user_id))
        )
        db.connection.commit()
        return self.get_balance(guild_id, user_id)

    def remove_balance(self, guild_id, user_id, amount):
        """Returns False (and leaves the balance untouched) if funds are
        insufficient, True if the amount was deducted. Used by every game
        and /buy to spend Aura."""
        entry = self.ensure_account(guild_id, user_id)
        if entry["balance"] < amount:
            return False
        db.connection.execute(
            "UPDATE aura_accounts SET balance = balance - ? WHERE guild_id = ? AND user_id = ?",
            (amount, str(guild_id), str(user_id))
        )
        db.connection.commit()
        return True

    def set_balance(self, guild_id, user_id, amount):
        """Clamps to 0 - used by owner tools that adjust a balance directly
        rather than earning/spending it."""
        self.ensure_account(guild_id, user_id)
        db.connection.execute(
            "UPDATE aura_accounts SET balance = ? WHERE guild_id = ? AND user_id = ?",
            (max(0, amount), str(guild_id), str(user_id))
        )
        db.connection.commit()
        return self.get_balance(guild_id, user_id)

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

    @app_commands.command(name="richest", description="Show the Aura leaderboard")
    @app_commands.describe(scope="This server only, or aggregated across every server the bot is in")
    @app_commands.choices(scope=[
        app_commands.Choice(name="This server", value="server"),
        app_commands.Choice(name="Global (all servers)", value="global"),
    ])
    async def richest(self, interaction: discord.Interaction, scope: app_commands.Choice[str] = None):
        scope_value = scope.value if scope else "server"

        if scope_value == "server":
            if not interaction.guild:
                await interaction.response.send_message("Server scope only works inside a server.", ephemeral=True)
                return
            rows = db.connection.execute(
                "SELECT user_id, balance FROM aura_accounts WHERE guild_id = ? ORDER BY balance DESC LIMIT 10",
                (str(interaction.guild.id),)
            ).fetchall()
            title = f"Richest - {interaction.guild.name}"
        else:
            rows = db.connection.execute(
                "SELECT user_id, SUM(balance) AS balance FROM aura_accounts GROUP BY user_id ORDER BY balance DESC LIMIT 10"
            ).fetchall()
            title = "Global Richest (all servers combined)"

        if not rows:
            await interaction.response.send_message("No Aura data yet.", ephemeral=True)
            return

        await interaction.response.defer()

        entries = []
        for rank, row in enumerate(rows, start=1):
            user = self.bot.get_user(int(row["user_id"]))
            name = user.display_name if user else f"Unknown User ({row['user_id']})"
            avatar_bytes = None
            if user:
                try:
                    avatar_bytes = await user.display_avatar.with_size(128).read()
                except discord.HTTPException:
                    avatar_bytes = None
            entries.append({
                "rank": rank, "name": name, "avatar_bytes": avatar_bytes,
                "value_text": f"{row['balance']} Aura"
            })

        buffer = generate_leaderboard_card(title, entries)
        await interaction.followup.send(file=discord.File(buffer, filename="richest.png"))

    @app_commands.command(name="daily", description="Claim your daily Aura")
    async def daily(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        entry = self.ensure_account(interaction.guild.id, interaction.user.id)
        now = time.time()
        last_daily = entry["last_daily"]
        streak = entry["daily_streak"]

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
                streak = 0

        streak += 1
        bonus = min((streak - 1) * DAILY_STREAK_BONUS_PER_DAY, DAILY_STREAK_BONUS_CAP)
        base = random.randint(DAILY_MIN, DAILY_MAX)
        total = base + bonus

        db.connection.execute(
            "UPDATE aura_accounts SET balance = balance + ?, last_daily = ?, daily_streak = ? WHERE guild_id = ? AND user_id = ?",
            (total, now, streak, str(interaction.guild.id), str(interaction.user.id))
        )
        db.connection.commit()
        new_balance = self.get_balance(interaction.guild.id, interaction.user.id)

        embed = discord.Embed(
            title="💰 Daily Aura Claimed",
            description=(
                f"You claimed **{total}** Aura ({base} base + {bonus} streak bonus).\n"
                f"🔥 Streak: **{streak}** day{'s' if streak != 1 else ''}\n"
                f"Balance: **{new_balance}** Aura"
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
        last_scavenge = entry["last_scavenge"]

        if last_scavenge is not None and now - last_scavenge < SCAVENGE_COOLDOWN:
            minutes = int(SCAVENGE_COOLDOWN - (now - last_scavenge)) // 60 + 1
            await interaction.response.send_message(
                f"⏳ You already scavenged recently. Try again in **{minutes}m**.",
                ephemeral=True
            )
            return

        guild_id, user_id = str(interaction.guild.id), str(interaction.user.id)

        if random.random() < SCAVENGE_NOTHING_CHANCE:
            db.connection.execute(
                "UPDATE aura_accounts SET last_scavenge = ? WHERE guild_id = ? AND user_id = ?",
                (now, guild_id, user_id)
            )
            db.connection.commit()
            embed = discord.Embed(
                title="🔍 Scavenge",
                description=random.choice(SCAVENGE_NOTHING_FLAVOR),
                color=discord.Color.dark_grey()
            )
            await interaction.response.send_message(embed=embed)
            return

        amount = random.randint(SCAVENGE_MIN, SCAVENGE_MAX)
        db.connection.execute(
            "UPDATE aura_accounts SET balance = balance + ?, last_scavenge = ? WHERE guild_id = ? AND user_id = ?",
            (amount, now, guild_id, user_id)
        )
        db.connection.commit()
        new_balance = self.get_balance(interaction.guild.id, interaction.user.id)

        flavor = random.choice(SCAVENGE_FLAVOR).format(amount=amount)
        embed = discord.Embed(
            title="🔍 Scavenge",
            description=f"{flavor}\nBalance: **{new_balance}** Aura",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Aura(bot))
