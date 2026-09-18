import discord
from discord.ext import commands
from discord import app_commands, ui
import re
import time
from collections import defaultdict

import db

class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = defaultdict(list)
        print("[DEBUG] Automod cog loaded")

    def get_guild_config(self, guild_id):
        guild_id = str(guild_id)
        row = db.connection.execute("SELECT * FROM automod_config WHERE guild_id = ?", (guild_id,)).fetchone()
        if row is None:
            db.connection.execute("INSERT INTO automod_config (guild_id) VALUES (?)", (guild_id,))
            db.connection.commit()
            row = db.connection.execute("SELECT * FROM automod_config WHERE guild_id = ?", (guild_id,)).fetchone()

        cfg = dict(row)
        cfg["link_filter"] = bool(cfg["link_filter"])
        cfg["promotion_filter"] = bool(cfg["promotion_filter"])
        cfg["blacklisted_words"] = [
            r["word"] for r in db.connection.execute(
                "SELECT word FROM automod_blacklisted_words WHERE guild_id = ?", (guild_id,)
            ).fetchall()
        ]
        return cfg

    def set_guild_config(self, guild_id, **kwargs):
        guild_id = str(guild_id)
        self.get_guild_config(guild_id)  # ensure a row exists first
        words = kwargs.pop("blacklisted_words", None)
        if kwargs:
            values = [int(v) if isinstance(v, bool) else v for v in kwargs.values()]
            set_clause = ", ".join(f"{k} = ?" for k in kwargs)
            db.connection.execute(f"UPDATE automod_config SET {set_clause} WHERE guild_id = ?", (*values, guild_id))
        if words is not None:
            db.connection.execute("DELETE FROM automod_blacklisted_words WHERE guild_id = ?", (guild_id,))
            for word in words:
                db.connection.execute(
                    "INSERT INTO automod_blacklisted_words (guild_id, word) VALUES (?, ?)", (guild_id, word)
                )
        db.connection.commit()

    async def warn_user(self, guild_id, member: discord.Member, reason: str):
        warnings_cog = self.bot.get_cog("Warnings")
        if warnings_cog:
            await warnings_cog.warn_manual(guild_id, member, reason)
            total_warnings = len(warnings_cog.get_warnings(member.id))
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

            if self.selected_level == "low":
                self.cog.set_guild_config(
                    self.guild_id, spam_threshold=10, caps_limit=90, mention_limit=5,
                    link_filter=True, promotion_filter=True, blacklisted_words=[]
                )
            elif self.selected_level == "medium":
                self.cog.set_guild_config(
                    self.guild_id, spam_threshold=5, caps_limit=70, mention_limit=3,
                    link_filter=True, promotion_filter=True, blacklisted_words=[]
                )
            elif self.selected_level == "high":
                self.cog.set_guild_config(
                    self.guild_id, spam_threshold=3, caps_limit=50, mention_limit=2,
                    link_filter=True, promotion_filter=True, blacklisted_words=["badword1", "badword2"]
                )

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
