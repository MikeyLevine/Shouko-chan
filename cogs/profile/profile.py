import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re

from .card import generate_profile_card, DEFAULT_ACCENT

MAX_BIO_LENGTH = 100
HEX_RE = re.compile(r'^#?[0-9a-fA-F]{6}$')


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/profiles.json"
        self.profiles = self.load_data()
        print("[DEBUG] Profile cog loaded")

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                return json.load(f)
        return {}

    def save_data(self):
        with open(self.data_file, "w") as f:
            json.dump(self.profiles, f, indent=4)

    def get_entry(self, user_id):
        return self.profiles.setdefault(str(user_id), {"color": DEFAULT_ACCENT, "bio": ""})

    @app_commands.command(name="setbio", description="Set your profile bio")
    @app_commands.describe(text=f"Your bio text (max {MAX_BIO_LENGTH} characters)")
    async def setbio(self, interaction: discord.Interaction, text: app_commands.Range[str, 0, MAX_BIO_LENGTH]):
        self.get_entry(interaction.user.id)["bio"] = text
        self.save_data()
        await interaction.response.send_message("✅ Bio updated.", ephemeral=True)

    @app_commands.command(name="setcolor", description="Set your profile accent color (hex, e.g. #ff5500)")
    @app_commands.describe(hex_color="A hex color like #ff5500 or ff5500")
    async def setcolor(self, interaction: discord.Interaction, hex_color: str):
        if not HEX_RE.match(hex_color):
            await interaction.response.send_message("Invalid hex color. Use a format like `#ff5500`.", ephemeral=True)
            return
        if not hex_color.startswith('#'):
            hex_color = '#' + hex_color
        self.get_entry(interaction.user.id)["color"] = hex_color
        self.save_data()
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

        guild_data = leveling_cog.user_data.get(str(interaction.guild.id), {}) if leveling_cog else {}
        entry = guild_data.get(str(target.id), {"exp": 0})

        if leveling_cog:
            level, exp_into_level, exp_needed = leveling_cog.get_level_progress(entry.get("exp", 0))
        else:
            level, exp_into_level, exp_needed = 1, 0, 100

        ranked = sorted(guild_data.items(), key=lambda item: item[1].get("exp", 0), reverse=True)
        rank = next((i + 1 for i, (uid, _) in enumerate(ranked) if uid == str(target.id)), None)

        aura_balance = aura_cog.get_balance(interaction.guild.id, target.id) if aura_cog else 0
        profile_data = self.get_entry(target.id)

        shop_cog = self.bot.get_cog("Shop")
        prefix_text, title_text, nickname = ("", None, None)
        if shop_cog:
            prefix_text, title_text, nickname = shop_cog.get_display_extras(interaction.guild.id, target.id)

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
            total_ranked=len(ranked),
            aura_balance=aura_balance,
            bio=profile_data.get("bio", ""),
            accent_hex=profile_data.get("color", DEFAULT_ACCENT),
            prefix_text=prefix_text,
            title_text=title_text,
        )

        await interaction.followup.send(file=discord.File(buffer, filename="profile.png"))

async def setup(bot):
    await bot.add_cog(Profile(bot))
