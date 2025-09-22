import discord
from discord.ext import commands
from discord import app_commands
import random

class RPS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] RPS cog loaded")

    @app_commands.command(name="rps", description="Play Rock-Paper-Scissors against the bot!")
    async def rps(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🪨 📜 ✂️ Rock Paper Scissors",
            description="Click a button to play!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, view=RPSView())


class RPSView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)  # buttons active for 30 seconds

    @discord.ui.button(label="Rock 🪨", style=discord.ButtonStyle.blurple)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Rock")

    @discord.ui.button(label="Paper 📜", style=discord.ButtonStyle.green)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Paper")

    @discord.ui.button(label="Scissors ✂️", style=discord.ButtonStyle.red)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Scissors")

    async def play(self, interaction: discord.Interaction, player_choice: str):
        choices = ["Rock", "Paper", "Scissors"]
        bot_choice = random.choice(choices)

        # Determine winner
        if player_choice == bot_choice:
            result = "🤝 It's a tie!"
        elif (player_choice == "Rock" and bot_choice == "Scissors") or \
             (player_choice == "Paper" and bot_choice == "Rock") or \
             (player_choice == "Scissors" and bot_choice == "Paper"):
            result = "🎉 You win!"
        else:
            result = "😢 You lose!"

        embed = discord.Embed(
            title="🪨 📜 ✂️ Rock Paper Scissors",
            description=f"**You chose:** {player_choice}\n**Bot chose:** {bot_choice}\n\n{result}",
            color=discord.Color.orange()
        )

        # Send ephemeral so only the user sees it
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(RPS(bot))
