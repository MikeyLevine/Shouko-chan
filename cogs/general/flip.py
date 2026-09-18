import discord
from discord.ext import commands
from discord import app_commands
import random
import traceback

class CoinFlip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] CoinFlip cog loaded")

    @app_commands.command(name="flip", description="Flip a coin, optionally betting Aura on your call")
    @app_commands.describe(bet="Optional: wager Aura on the result", call="Required if betting: your guess")
    @app_commands.choices(call=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails"),
    ])
    async def flip(
        self,
        interaction: discord.Interaction,
        bet: app_commands.Range[int, 1, None] = None,
        call: app_commands.Choice[str] = None,
    ):
        if bet:
            if not call:
                await interaction.response.send_message("You need to call heads or tails to bet.", ephemeral=True)
                return
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

            result = random.choice(["heads", "tails"])
            won = result == call.value
            lines = [f"**Result:** {result.capitalize()}", f"**Your call:** {call.value.capitalize()}"]

            if won:
                aura_cog.add_balance(interaction.guild.id, interaction.user.id, bet * 2)
                lines.append(f"\n🎉 You win! **+{bet}** Aura")
            else:
                lines.append(f"\n😢 You lose! **-{bet}** Aura")
            lines.append(f"Balance: {aura_cog.get_balance(interaction.guild.id, interaction.user.id)} Aura")

            embed = discord.Embed(
                title="🪙 Coin Flip",
                description="\n".join(lines),
                color=discord.Color.gold() if won else discord.Color.red()
            )
            embed.set_footer(text=f"Flipped by {interaction.user.display_name}")
            await interaction.response.send_message(embed=embed)
            return

        # Free flip - unchanged reusable "Flip Again" panel, no wager involved.
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
