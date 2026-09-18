import discord
from discord.ext import commands
from discord import app_commands
from collections import Counter
import random

MIN_BET = 10
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
RANK_VALUE = {rank: i for i, rank in enumerate(RANKS, start=2)}  # 2..14, A=14

# Standard Jacks-or-Better paytable. Values are the TOTAL return multiplier
# (i.e. what you get back, not profit) - a pair of Jacks paying 1 just
# returns your bet, matching how real machines list these.
PAYTABLE = [
    ("Royal Flush", 250),
    ("Straight Flush", 50),
    ("Four of a Kind", 25),
    ("Full House", 9),
    ("Flush", 6),
    ("Straight", 4),
    ("Three of a Kind", 3),
    ("Two Pair", 2),
    ("Jacks or Better", 1),
]
PAYOUT_MAP = dict(PAYTABLE)


def new_deck():
    deck = [f"{rank}{suit}" for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def card_rank(card):
    return card[:-1]  # suit is always the last character


def card_suit(card):
    return card[-1]


def evaluate_hand(hand):
    """Returns the winning hand name, or None if it doesn't qualify."""
    ranks = [card_rank(c) for c in hand]
    suits = [card_suit(c) for c in hand]
    values = sorted(RANK_VALUE[r] for r in ranks)

    is_flush = len(set(suits)) == 1

    unique_values = sorted(set(values))
    is_straight = False
    if len(unique_values) == 5:
        if unique_values[-1] - unique_values[0] == 4:
            is_straight = True
        elif unique_values == [2, 3, 4, 5, 14]:  # Ace-low straight (A-2-3-4-5)
            is_straight = True

    counts = Counter(ranks)
    count_values = sorted(counts.values(), reverse=True)

    if is_straight and is_flush:
        if set(values) == {10, 11, 12, 13, 14}:
            return "Royal Flush"
        return "Straight Flush"
    if count_values[0] == 4:
        return "Four of a Kind"
    if count_values[0] == 3 and count_values[1] == 2:
        return "Full House"
    if is_flush:
        return "Flush"
    if is_straight:
        return "Straight"
    if count_values[0] == 3:
        return "Three of a Kind"
    if count_values[0] == 2 and count_values[1] == 2:
        return "Two Pair"
    if count_values[0] == 2:
        pair_rank = next(r for r, c in counts.items() if c == 2)
        if pair_rank in ("J", "Q", "K", "A"):
            return "Jacks or Better"
    return None


def payout_multiplier(hand_name):
    return PAYOUT_MAP.get(hand_name, 0)


class HoldButton(discord.ui.Button):
    def __init__(self, index, card):
        super().__init__(label=card, style=discord.ButtonStyle.secondary, row=0)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: VideoPokerView = self.view
        if interaction.user.id != view.user_id:
            await interaction.response.send_message("This isn't your game.", ephemeral=True)
            return
        view.held[self.index] = not view.held[self.index]
        self.style = discord.ButtonStyle.success if view.held[self.index] else discord.ButtonStyle.secondary
        self.label = f"{view.hand[self.index]} 🔒" if view.held[self.index] else view.hand[self.index]
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


class DrawButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Draw", style=discord.ButtonStyle.primary, row=1)

    async def callback(self, interaction: discord.Interaction):
        view: VideoPokerView = self.view
        if interaction.user.id != view.user_id:
            await interaction.response.send_message("This isn't your game.", ephemeral=True)
            return
        await view.draw_and_resolve(interaction)


class VideoPokerView(discord.ui.View):
    def __init__(self, bot, guild_id, user_id, bet, deck, hand):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.bet = bet
        self.deck = deck
        self.hand = hand
        self.held = [False] * 5
        self.resolved = False
        self.message = None

        for i, card in enumerate(hand):
            self.add_item(HoldButton(i, card))
        self.add_item(DrawButton())

    def build_embed(self, result_text=None):
        embed = discord.Embed(title="🎴 Video Poker - Jacks or Better", color=discord.Color.blurple())
        if result_text:
            embed.description = result_text
        embed.add_field(name="Your hand", value="  ".join(self.hand), inline=False)
        held_positions = [str(i + 1) for i, held in enumerate(self.held) if held]
        embed.add_field(name="Held", value=", ".join(held_positions) if held_positions else "None", inline=False)
        embed.add_field(name="Bet", value=f"{self.bet} Aura", inline=False)
        return embed

    async def draw_and_resolve(self, interaction):
        self.resolved = True
        for i in range(5):
            if not self.held[i]:
                self.hand[i] = self.deck.pop()

        for child in self.children:
            child.disabled = True

        hand_name = evaluate_hand(self.hand)
        multiplier = payout_multiplier(hand_name)
        aura_cog = self.bot.get_cog("Aura")

        if multiplier > 0:
            payout = self.bet * multiplier
            aura_cog.add_balance(self.guild_id, self.user_id, payout)
            result_text = f"🎉 {hand_name}! You win **{payout}** Aura ({multiplier}x)"
        else:
            result_text = "😢 No winning hand."

        new_balance = aura_cog.get_balance(self.guild_id, self.user_id)
        embed = self.build_embed(result_text=result_text)
        embed.set_footer(text=f"Balance: {new_balance} Aura")

        if interaction is not None:
            await interaction.response.edit_message(embed=embed, view=self)
        elif self.message is not None:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass

    async def on_timeout(self):
        if self.resolved:
            return
        # Auto-draw (holding whatever was held) rather than leaving a bet stuck.
        await self.draw_and_resolve(None)


class VideoPoker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] VideoPoker cog loaded")

    @app_commands.command(name="poker", description="Play Jacks or Better video poker with your Aura")
    @app_commands.describe(bet="How much Aura to bet")
    async def poker(self, interaction: discord.Interaction, bet: app_commands.Range[int, MIN_BET, None]):
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

        deck = new_deck()
        hand = [deck.pop() for _ in range(5)]

        view = VideoPokerView(self.bot, interaction.guild.id, interaction.user.id, bet, deck, hand)
        await interaction.response.send_message(embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(VideoPoker(bot))
