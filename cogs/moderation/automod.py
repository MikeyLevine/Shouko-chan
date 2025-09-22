import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import os
import re
import time
from collections import defaultdict
import shutil

CONFIG_FILE = "data/automod_config.json"
BACKUP_FILE = "data/automod_config_backup.json"

class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = defaultdict(list)
        self.config = self.load_config()
        print("[DEBUG] Automod cog loaded")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.save_config({})
            return {}

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Config root must be a dictionary")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[WARN] automod_config.json is corrupted: {e}. Creating backup and resetting.")
            shutil.copy(CONFIG_FILE, BACKUP_FILE)
            self.save_config({})
            return {}

    def save_config(self, data=None):
        if data is not None:
            self.config = data
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)
        print("[DEBUG] Automod config saved")

    def get_guild_config(self, guild_id):
        guild_id = str(guild_id)
        if guild_id not in self.config:
            self.config[guild_id] = {
                "spam_threshold": 5,
                "caps_limit": 70,
                "mention_limit": 5,
                "link_filter": True,
                "promotion_filter": True,
                "blacklisted_words": [],
                "auto_mute_threshold": 3,
                "auto_kick_threshold": 5
            }
            self.save_config()
        return self.config[guild_id]

    async def warn_user(self, guild_id, member: discord.Member, reason: str):
        warnings_cog = self.bot.get_cog("Warnings")
        if warnings_cog:
            await warnings_cog.warn_manual(guild_id, member, reason)
            total_warnings = len(warnings_cog.warnings.get(str(member.id), []))
            guild_cfg = self.get_guild_config(guild_id)
            if total_warnings >= guild_cfg.get("auto_kick_threshold", 5):
                await member.kick(reason="Reached auto-kick threshold")
            elif total_warnings >= guild_cfg.get("auto_mute_threshold", 3):
                mute_role = discord.utils.get(member.guild.roles, name="Muted")
                if mute_role:
                    await member.add_roles(mute_role, reason="Reached auto-mute threshold")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_cfg = self.get_guild_config(message.guild.id)

        now = time.time()
        self.message_cache[message.author.id].append((now, message.content))
        self.message_cache[message.author.id] = [(t, m) for t, m in self.message_cache[message.author.id] if now - t <= 10]

        if len(self.message_cache[message.author.id]) > guild_cfg["spam_threshold"]:
            await message.delete()
            await self.warn_user(message.guild.id, message.author, "Spamming messages")
            return

        letters = [c for c in message.content if c.isalpha()]
        if letters:
            caps_percentage = sum(1 for c in letters if c.isupper()) / len(letters) * 100
            if caps_percentage > guild_cfg["caps_limit"]:
                await message.delete()
                await self.warn_user(message.guild.id, message.author, "Excessive capital letters")
                return

        if len(message.mentions) > guild_cfg["mention_limit"]:
            await message.delete()
            await self.warn_user(message.guild.id, message.author, "Too many mentions")
            return

        if guild_cfg.get("link_filter", True):
            if re.search(r"https?://\S+", message.content):
                await message.delete()
                await self.warn_user(message.guild.id, message.author, "Posting links is not allowed")
                return

        if guild_cfg.get("promotion_filter", True):
            if re.search(r"(discord\.gg|discord\.com/invite)/\S+", message.content):
                await message.delete()
                await self.warn_user(message.guild.id, message.author, "Posting server invites is not allowed")
                return

        for word in guild_cfg.get("blacklisted_words", []):
            if word.lower() in message.content.lower():
                await message.delete()
                await self.warn_user(message.guild.id, message.author, f"Used blacklisted word: {word}")
                return

    class AutomodSetupView(ui.View):
        def __init__(self, cog, guild_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.guild_id = str(guild_id)
            self.selected_level = None

            # Dropdown
            self.select = ui.Select(
                placeholder="Select moderation level...",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label="Low", description="Basic link detection", value="low"),
                    discord.SelectOption(label="Medium", description="Link + spam prevention", value="medium"),
                    discord.SelectOption(label="High", description="Link + spam + swear word detection", value="high")
                ]
            )
            self.select.callback = self.select_callback
            self.add_item(self.select)

            # Finish button
            self.finish_btn = ui.Button(label="Finish", style=discord.ButtonStyle.green)
            self.finish_btn.callback = self.finish_callback
            self.add_item(self.finish_btn)

        async def select_callback(self, interaction: discord.Interaction):
            self.selected_level = self.select.values[0]
            await interaction.response.send_message(
                f"Selected moderation level: **{self.selected_level}**. Click Finish to save.",
                ephemeral=True
            )

        async def finish_callback(self, interaction: discord.Interaction):
            if not self.selected_level:
                await interaction.response.send_message(
                    "You must select a moderation level first!", ephemeral=True
                )
                return

            cfg = self.cog.get_guild_config(self.guild_id)

            if self.selected_level == "low":
                cfg.update({
                    "spam_threshold": 10,
                    "caps_limit": 90,
                    "mention_limit": 5,
                    "link_filter": True,
                    "promotion_filter": True,
                    "blacklisted_words": []
                })
            elif self.selected_level == "medium":
                cfg.update({
                    "spam_threshold": 5,
                    "caps_limit": 70,
                    "mention_limit": 3,
                    "link_filter": True,
                    "promotion_filter": True,
                    "blacklisted_words": []
                })
            elif self.selected_level == "high":
                cfg.update({
                    "spam_threshold": 3,
                    "caps_limit": 50,
                    "mention_limit": 2,
                    "link_filter": True,
                    "promotion_filter": True,
                    "blacklisted_words": ["badword1", "badword2"]
                })

            self.cog.save_config()
            await interaction.response.send_message(
                f"Automod setup saved! Level: **{self.selected_level}**", ephemeral=True
            )

    @app_commands.command(name="automodsetup", description="Configure automod for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def automodsetup(self, interaction: discord.Interaction):
        view = self.AutomodSetupView(self, interaction.guild.id)
        await interaction.response.send_message(
            "Select the moderation level for this server:",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Automod(bot))
