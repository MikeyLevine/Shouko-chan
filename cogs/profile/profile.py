import discord
from discord.ext import commands
from discord import app_commands
import re

import db
from .card import generate_profile_card, DEFAULT_ACCENT

MAX_BIO_LENGTH = 100
HEX_RE = re.compile(r'^#?[0-9a-fA-F]{6}$')


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Profile cog loaded")

    def get_entry(self, user_id):
        user_id = str(user_id)
        row = db.connection.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            db.connection.execute("INSERT INTO profiles (user_id) VALUES (?)", (user_id,))
            db.connection.commit()
            row = db.connection.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return row

    @app_commands.command(name="setbio", description="Set your profile bio")
    @app_commands.describe(text=f"Your bio text (max {MAX_BIO_LENGTH} characters)")
    async def setbio(self, interaction: discord.Interaction, text: app_commands.Range[str, 0, MAX_BIO_LENGTH]):
        self.get_entry(interaction.user.id)
        db.connection.execute("UPDATE profiles SET bio = ? WHERE user_id = ?", (text, str(interaction.user.id)))
        db.connection.commit()
        await interaction.response.send_message("✅ Bio updated.", ephemeral=True)

    @app_commands.command(name="setcolor", description="Set your profile accent color (hex, e.g. #ff5500)")
    @app_commands.describe(hex_color="A hex color like #ff5500 or ff5500")
    async def setcolor(self, interaction: discord.Interaction, hex_color: str):
        if not HEX_RE.match(hex_color):
            await interaction.response.send_message("Invalid hex color. Use a format like `#ff5500`.", ephemeral=True)
            return
        if not hex_color.startswith('#'):
            hex_color = '#' + hex_color
        self.get_entry(interaction.user.id)
        db.connection.execute("UPDATE profiles SET color = ? WHERE user_id = ?", (hex_color, str(interaction.user.id)))
        db.connection.commit()
        await interaction.response.send_message(f"✅ Accent color set to `{hex_color}`.", ephemeral=True)

    @app_commands.command(name="profile", description="Show your (or someone else's) profile card")
    @app_commands.describe(member="Whose profile to show")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        target = member or interaction.user
        leveling_cog = self.bot.get_cog("Leveling")
        aura_cog = self.bot.get_cog("Aura")

        if leveling_cog:
            exp = leveling_cog.get_exp(interaction.guild.id, target.id)
            level, exp_into_level, exp_needed = leveling_cog.get_level_progress(exp)
            rank, total_ranked = leveling_cog.get_rank(interaction.guild.id, target.id)
        else:
            level, exp_into_level, exp_needed, rank, total_ranked = 1, 0, 100, None, 0

        aura_balance = aura_cog.get_balance(interaction.guild.id, target.id) if aura_cog else 0
        profile_data = self.get_entry(target.id)

        shop_cog = self.bot.get_cog("Shop")
        prefix_text, title_text, nickname, background_id = ("", None, None, None)
        if shop_cog:
            prefix_text, title_text, nickname, background_id = shop_cog.get_display_extras(interaction.guild.id, target.id)

        try:
            avatar_bytes = await target.display_avatar.with_size(256).read()
        except discord.HTTPException:
            avatar_bytes = None

        buffer = generate_profile_card(
            username=nickname or target.display_name,
            avatar_bytes=avatar_bytes,
            level=level,
            exp_into_level=exp_into_level,
            exp_needed_for_level=exp_needed,
            rank=rank,
            total_ranked=total_ranked,
            aura_balance=aura_balance,
            bio=profile_data["bio"],
            accent_hex=profile_data["color"],
            prefix_text=prefix_text,
            title_text=title_text,
            background_id=background_id,
        )

        await interaction.followup.send(file=discord.File(buffer, filename="profile.png"))

async def setup(bot):
    await bot.add_cog(Profile(bot))
