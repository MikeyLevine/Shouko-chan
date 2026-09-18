import discord
from discord.ext import commands
from discord import app_commands
import random

MIN_BET = 10
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


def new_deck():
    deck = [f"{rank}{suit}" for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def card_value(card):
    rank = card[:-1]  # strip the suit, which is always the last character
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(hand):
    total = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[:-1] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def format_hand(hand, hide_first=False):
    if hide_first:
        return f"🂠 {' '.join(hand[1:])}"
    return " ".join(hand)


class BlackjackView(discord.ui.View):
    def __init__(self, bot, guild_id, user_id, bet, deck, player_hand, dealer_hand):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.bet = bet
        self.deck = deck
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.resolved = False
        self.message = None  # set by the caller right after sending

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game.", ephemeral=True)
            return False
        return True

    def build_embed(self, reveal_dealer=False, result_text=None):
        player_total = hand_value(self.player_hand)
        embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
        if result_text:
            embed.description = result_text
        embed.add_field(name="Your hand", value=f"{format_hand(self.player_hand)} (**{player_total}**)", inline=False)
        if reveal_dealer:
            dealer_total = hand_value(self.dealer_hand)
            embed.add_field(name="Dealer's hand", value=f"{format_hand(self.dealer_hand)} (**{dealer_total}**)", inline=False)
        else:
            embed.add_field(name="Dealer's hand", value=format_hand(self.dealer_hand, hide_first=True), inline=False)
        embed.add_field(name="Bet", value=f"{self.bet} Aura", inline=False)
        return embed

    async def _update(self, interaction, embed):
        if interaction is not None:
            await interaction.response.edit_message(embed=embed, view=self)
        elif self.message is not None:
            await self.message.edit(embed=embed, view=self)

    async def end_game(self, interaction, outcome):
        # outcome: "blackjack", "win", "push", or "lose"
        self.resolved = True
        for child in self.children:
            child.disabled = True

        aura_cog = self.bot.get_cog("Aura")

        if outcome == "blackjack":
            profit = int(self.bet * 1.5)
            aura_cog.add_balance(self.guild_id, self.user_id, self.bet + profit)
            result_text = f"🂡 Blackjack! You win **{profit}** Aura."
        elif outcome == "win":
            aura_cog.add_balance(self.guild_id, self.user_id, self.bet * 2)
            result_text = f"✅ You win **{self.bet}** Aura."
        elif outcome == "push":
            aura_cog.add_balance(self.guild_id, self.user_id, self.bet)
            result_text = "🤝 Push - your bet was returned."
        else:
            result_text = f"❌ You lost **{self.bet}** Aura."

        new_balance = aura_cog.get_balance(self.guild_id, self.user_id)
        embed = self.build_embed(reveal_dealer=True, result_text=result_text)
        embed.set_footer(text=f"Balance: {new_balance} Aura")
        await self._update(interaction, embed)

    async def dealer_play_and_resolve(self, interaction):
        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

        player_total = hand_value(self.player_hand)
        dealer_total = hand_value(self.dealer_hand)

        if dealer_total > 21 or player_total > dealer_total:
            outcome = "win"
        elif dealer_total > player_total:
            outcome = "lose"
        else:
            outcome = "push"
        await self.end_game(interaction, outcome)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player_hand.append(self.deck.pop())
        if hand_value(self.player_hand) > 21:
            await self.end_game(interaction, "lose")
            return
        await self._update(interaction, self.build_embed())

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.dealer_play_and_resolve(interaction)

    async def on_timeout(self):
        if self.resolved:
            return
        # Auto-stand rather than leaving the bet in limbo forever.
        await self.dealer_play_and_resolve(None)


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Blackjack cog loaded")  # Debug output

    @app_commands.command(name="blackjack", description="Play a game of blackjack with your Aura")
    @app_commands.describe(bet="How much Aura to bet")
    async def blackjack(self, interaction: discord.Interaction, bet: app_commands.Range[int, MIN_BET, None]):
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
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        view = BlackjackView(self.bot, interaction.guild.id, interaction.user.id, bet, deck, player_hand, dealer_hand)

        await interaction.response.send_message(embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()

        if hand_value(player_hand) == 21:
            outcome = "push" if hand_value(dealer_hand) == 21 else "blackjack"
            await view.end_game(None, outcome)

async def setup(bot):
    await bot.add_cog(Blackjack(bot))
