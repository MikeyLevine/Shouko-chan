import discord
from discord.ext import commands
from discord import app_commands
import random
import traceback

class CoinFlip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] CoinFlip cog loaded")

    @app_commands.command(name="flip", description="Flip a coin!")
    async def flip(self, interaction: discord.Interaction):
        result = random.randint(0, 1)

        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"**Result:** {'Heads' if result == 0 else 'Tails'}",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Flipped by {interaction.user.display_name}")

        view = CoinFlipView()
        await interaction.response.send_message(embed=embed, view=view)


class CoinFlipView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Flip Again",
        style=discord.ButtonStyle.blurple,
        emoji="🔄"
    )
    async def flip_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            result = random.randint(0, 1)

            embed = discord.Embed(
                title="🪙 Coin Flip",
                description=f"**Result:** {'Heads' if result == 0 else 'Tails'}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Flipped by {interaction.user.display_name}")

            # ✅ Instead of editing the old one, send a NEW message
            await interaction.response.send_message(embed=embed, view=CoinFlipView())

        except Exception as e:
            traceback.print_exc()
            try:
                await interaction.response.send_message(
                    f"⚠️ Button failed due to: `{e}`",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    f"⚠️ Button failed due to: `{e}`",
                    ephemeral=True
                )


async def setup(bot):
    await bot.add_cog(CoinFlip(bot))
