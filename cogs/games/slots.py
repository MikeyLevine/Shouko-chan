import discord
from discord.ext import commands
from discord import app_commands
import random

MIN_BET = 10

# (symbol, spin weight) - lower weight = rarer.
SYMBOLS = [
    ("🍒", 40),
    ("🍋", 30),
    ("🍊", 20),
    ("🍉", 15),
    ("⭐", 8),
    ("💎", 4),
    ("7️⃣", 2),
]

# Payout multiplier for landing three of a symbol.
JACKPOT_MULTIPLIERS = {
    "7️⃣": 20,
    "💎": 12,
    "⭐": 8,
    "🍉": 5,
    "🍊": 4,
    "🍋": 3,
    "🍒": 2,
}
PAIR_MULTIPLIER = 1.5  # any two matching symbols out of the three reels


def spin():
    symbols, weights = zip(*SYMBOLS)
    return random.choices(symbols, weights=weights, k=3)


def resolve(reels, bet):
    if reels[0] == reels[1] == reels[2]:
        winnings = bet * JACKPOT_MULTIPLIERS[reels[0]]
        return winnings, f"🎉 Jackpot! Three {reels[0]} in a row!"
    if reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        winnings = int(bet * PAIR_MULTIPLIER)
        return winnings, "✨ Two matching symbols!"
    return 0, "No match - better luck next time."


class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Slots cog loaded")  # Debug output

    @app_commands.command(name="slots", description="Spin the slot machine with your Aura")
    @app_commands.describe(bet="How much Aura to bet")
    async def slots(self, interaction: discord.Interaction, bet: app_commands.Range[int, MIN_BET, None]):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        aura_cog = self.bot.get_cog("Aura")
        if not aura_cog:
            await interaction.response.send_message("⚠️ Aura system is not available right now.", ephemeral=True)
            return

        if not aura_cog.remove_balance(interaction.guild.id, interaction.user.id, bet):
            await interaction.response.send_message("You don't have enough Aura for that bet.", ephemeral=True)
            return

        reels = spin()
        winnings, result_text = resolve(reels, bet)

        if winnings > 0:
            aura_cog.add_balance(interaction.guild.id, interaction.user.id, winnings)

        net = winnings - bet
        new_balance = aura_cog.get_balance(interaction.guild.id, interaction.user.id)

        embed = discord.Embed(
            title="🎰 Slots",
            description=f"[ {' | '.join(reels)} ]\n\n{result_text}",
            color=discord.Color.gold() if winnings > 0 else discord.Color.red()
        )
        embed.add_field(name="Bet", value=f"{bet} Aura", inline=True)
        embed.add_field(name="Net", value=f"{'+' if net >= 0 else ''}{net} Aura", inline=True)
        embed.set_footer(text=f"Balance: {new_balance} Aura")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Slots(bot))
