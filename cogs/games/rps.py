import discord
from discord.ext import commands
from discord import app_commands
import random

class RPS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] RPS cog loaded")

    @app_commands.command(name="rps", description="Play Rock-Paper-Scissors against the bot")
    @app_commands.describe(bet="Optional: wager Aura on the outcome (win pays double, tie returns your bet)")
    async def rps(self, interaction: discord.Interaction, bet: app_commands.Range[int, 1, None] = None):
        if bet:
            if not interaction.guild:
                await interaction.response.send_message("Betting only works in a server.", ephemeral=True)
                return
            aura_cog = self.bot.get_cog("Aura")
            if not aura_cog:
                await interaction.response.send_message("⚠️ Aura system is not available right now.", ephemeral=True)
                return
            if not aura_cog.remove_balance(interaction.guild.id, interaction.user.id, bet):
                await interaction.response.send_message("You don't have enough Aura for that bet.", ephemeral=True)
                return

        description = "Click a button to play!"
        if bet:
            description += f"\nBet: **{bet}** Aura"

        embed = discord.Embed(
            title="🪨 📜 ✂️ Rock Paper Scissors",
            description=description,
            color=discord.Color.green()
        )
        guild_id = interaction.guild.id if interaction.guild else None
        view = RPSView(self.bot, guild_id, interaction.user.id, bet)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


class RPSView(discord.ui.View):
    def __init__(self, bot, guild_id, user_id, bet):
        # Free (unbetted) games never get disabled, so no need to time them
        # out; betted games need a timeout so a forgotten bet isn't stuck.
        super().__init__(timeout=30 if bet else None)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.bet = bet
        self.resolved = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Rock 🪨", style=discord.ButtonStyle.blurple)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Rock")

    @discord.ui.button(label="Paper 📜", style=discord.ButtonStyle.green)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Paper")

    @discord.ui.button(label="Scissors ✂️", style=discord.ButtonStyle.red)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Scissors")

    @staticmethod
    def _decide(player_choice, bot_choice):
        if player_choice == bot_choice:
            return "tie"
        beats = {"Rock": "Scissors", "Paper": "Rock", "Scissors": "Paper"}
        return "win" if beats[player_choice] == bot_choice else "lose"

    async def play(self, interaction: discord.Interaction, player_choice: str):
        if self.bet and self.resolved:
            return

        bot_choice = random.choice(["Rock", "Paper", "Scissors"])
        outcome = self._decide(player_choice, bot_choice)
        lines = [f"**You chose:** {player_choice}", f"**Bot chose:** {bot_choice}"]

        if self.bet:
            self.resolved = True
            for child in self.children:
                child.disabled = True

            aura_cog = self.bot.get_cog("Aura")
            if outcome == "win":
                aura_cog.add_balance(self.guild_id, self.user_id, self.bet * 2)
                lines.append(f"\n🎉 You win! **+{self.bet}** Aura")
            elif outcome == "tie":
                aura_cog.add_balance(self.guild_id, self.user_id, self.bet)
                lines.append("\n🤝 It's a tie! Your bet was returned.")
            else:
                lines.append(f"\n😢 You lose! **-{self.bet}** Aura")
            lines.append(f"Balance: {aura_cog.get_balance(self.guild_id, self.user_id)} Aura")

            embed = discord.Embed(
                title="🪨 📜 ✂️ Rock Paper Scissors",
                description="\n".join(lines),
                color=discord.Color.orange()
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            lines.append(
                "\n🤝 It's a tie!" if outcome == "tie"
                else "\n🎉 You win!" if outcome == "win"
                else "\n😢 You lose!"
            )
            embed = discord.Embed(
                title="🪨 📜 ✂️ Rock Paper Scissors",
                description="\n".join(lines),
                color=discord.Color.orange()
            )
            # Free games stay ephemeral per-click so the panel can be reused.
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_timeout(self):
        if not self.bet or self.resolved:
            return
        # Refund an unplayed bet rather than leaving it stuck.
        self.resolved = True
        for child in self.children:
            child.disabled = True
        aura_cog = self.bot.get_cog("Aura")
        aura_cog.add_balance(self.guild_id, self.user_id, self.bet)
        if self.message is not None:
            try:
                await self.message.edit(
                    content="⌛ Timed out - your bet was refunded.",
                    view=self
                )
            except discord.HTTPException:
                pass


async def setup(bot):
    await bot.add_cog(RPS(bot))
