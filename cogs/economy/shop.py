import discord
from discord.ext import commands
from discord import app_commands

import db

MAX_NICKNAME_LENGTH = 32
NICKNAME_TOKEN_PRICE = 2000

# Cosmetic catalog - plain constants, easy to add to/reprice later.
# Prefix symbols are checked against the card font's actual glyph coverage
# (via fontTools) before being added here - DejaVu Sans has no color-emoji
# glyphs, so anything from the pictographic emoji blocks renders as a tofu
# box on the card. Stick to the classic Miscellaneous Symbols/Dingbats
# ranges (U+2600-27BF) plus card-suit/chess symbols, which DejaVu covers.
TITLES = [
    {"id": "rookie", "name": "Rookie", "price": 100},
    {"id": "regular", "name": "Regular", "price": 200},
    {"id": "grinder", "name": "Grinder", "price": 500},
    {"id": "high_roller", "name": "High Roller", "price": 1000},
    {"id": "big_spender", "name": "Big Spender", "price": 2500},
    {"id": "whale_hunter", "name": "Whale Hunter", "price": 4000},
    {"id": "legend", "name": "Legend", "price": 5000},
    {"id": "degenerate", "name": "Degenerate", "price": 7500},
    {"id": "aura_whale", "name": "Aura Whale", "price": 10000},
    {"id": "ascended", "name": "Ascended", "price": 20000},
]
PREFIXES = [
    {"id": "star", "name": "★", "price": 300},
    {"id": "hollow_star", "name": "☆", "price": 300},
    {"id": "spade", "name": "♠", "price": 500},
    {"id": "heart", "name": "♥", "price": 500},
    {"id": "club", "name": "♣", "price": 500},
    {"id": "vip", "name": "[VIP]", "price": 1500},
    {"id": "lightning", "name": "⚡", "price": 2000},
    {"id": "crown", "name": "♛", "price": 3000},
    {"id": "swords", "name": "⚔", "price": 4000},
    {"id": "gem", "name": "◆", "price": 5000},
    {"id": "skull", "name": "☠", "price": 6000},
]
# ids match cogs/profile/card.py's BACKGROUND_STYLES (minus "midnight",
# which is the free default and isn't sold here).
BACKGROUNDS = [
    {"id": "sunset", "name": "Sunset", "price": 1500},
    {"id": "ocean", "name": "Ocean", "price": 1500},
    {"id": "forest", "name": "Forest", "price": 1500},
    {"id": "carbon", "name": "Carbon", "price": 2000},
    {"id": "neon", "name": "Neon", "price": 2500},
    {"id": "galaxy", "name": "Galaxy", "price": 3000},
]

TITLES_BY_ID = {t["id"]: t for t in TITLES}
PREFIXES_BY_ID = {p["id"]: p for p in PREFIXES}
BACKGROUNDS_BY_ID = {b["id"]: b for b in BACKGROUNDS}

# Generalizes buy/equip/inventory across the three item types instead of
# repeating near-identical branches for each.
CATALOGS = {"title": TITLES_BY_ID, "prefix": PREFIXES_BY_ID, "background": BACKGROUNDS_BY_ID}
CATALOG_LISTS = {"title": TITLES, "prefix": PREFIXES, "background": BACKGROUNDS}
SLOT_COLUMNS = {"title": "equipped_title", "prefix": "equipped_prefix", "background": "equipped_background"}


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Shop cog loaded")

    def ensure_profile(self, guild_id, user_id):
        guild_id, user_id = str(guild_id), str(user_id)
        row = db.connection.execute(
            "SELECT * FROM shop_profile WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ).fetchone()
        if row is None:
            db.connection.execute("INSERT INTO shop_profile (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
            db.connection.commit()
            row = db.connection.execute(
                "SELECT * FROM shop_profile WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
            ).fetchone()
        return row

    def get_owned(self, guild_id, user_id, item_type):
        rows = db.connection.execute(
            "SELECT item_id FROM shop_owned_items WHERE guild_id = ? AND user_id = ? AND item_type = ?",
            (str(guild_id), str(user_id), item_type)
        ).fetchall()
        return [r["item_id"] for r in rows]

    def owns(self, guild_id, user_id, item_type, item_id):
        row = db.connection.execute(
            "SELECT 1 FROM shop_owned_items WHERE guild_id = ? AND user_id = ? AND item_type = ? AND item_id = ?",
            (str(guild_id), str(user_id), item_type, item_id)
        ).fetchone()
        return row is not None

    def get_display_extras(self, guild_id, user_id):
        """Returns (prefix_text, title_text_or_none, nickname_or_none,
        background_id_or_none) for the profile card to render. Used by
        cogs.profile.profile."""
        row = self.ensure_profile(guild_id, user_id)
        prefix_text = ""
        if row["equipped_prefix"] in PREFIXES_BY_ID:
            prefix_text = PREFIXES_BY_ID[row["equipped_prefix"]]["name"]
        title_text = None
        if row["equipped_title"] in TITLES_BY_ID:
            title_text = TITLES_BY_ID[row["equipped_title"]]["name"]
        background_id = row["equipped_background"] if row["equipped_background"] in BACKGROUNDS_BY_ID else None
        return prefix_text, title_text, row["nickname"], background_id

    @app_commands.command(name="shop", description="Browse the Aura shop")
    async def shop(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        guild_id, user_id = interaction.guild.id, interaction.user.id
        profile = self.ensure_profile(guild_id, user_id)

        embed = discord.Embed(title="🛒 Aura Shop", color=discord.Color.blue())
        for item_type, label in (("title", "Titles"), ("prefix", "Prefixes"), ("background", "Backgrounds")):
            owned = self.get_owned(guild_id, user_id, item_type)
            embed.add_field(
                name=label,
                value="\n".join(
                    f"{'✅ ' if item['id'] in owned else ''}**{item['name']}** - {item['price']} Aura (`{item['id']}`)"
                    for item in CATALOG_LISTS[item_type]
                ),
                inline=False
            )
        embed.add_field(
            name="Custom Nickname",
            value="✅ Unlocked" if profile["nickname_unlocked"] else f"{NICKNAME_TOKEN_PRICE} Aura (`nickname_token`)",
            inline=False
        )
        embed.set_footer(text="Buy with /buy <id>  •  Equip with /equip")
        await interaction.response.send_message(embed=embed)

    async def _buy_autocomplete(self, interaction: discord.Interaction, current: str):
        owned = {}
        nickname_unlocked = False
        if interaction.guild:
            for item_type in CATALOGS:
                owned[item_type] = self.get_owned(interaction.guild.id, interaction.user.id, item_type)
            nickname_unlocked = bool(self.ensure_profile(interaction.guild.id, interaction.user.id)["nickname_unlocked"])

        current = current.lower()
        choices = []
        for item_type, catalog_list in CATALOG_LISTS.items():
            label = item_type.capitalize()
            for item in catalog_list:
                if item["id"] in owned.get(item_type, []):
                    continue
                if current in item["id"].lower() or current in item["name"].lower():
                    choices.append(app_commands.Choice(name=f"[{label}] {item['name']} - {item['price']} Aura", value=item["id"]))
        if not nickname_unlocked and current in "nickname_token":
            choices.append(app_commands.Choice(
                name=f"[Unlock] Custom Nickname - {NICKNAME_TOKEN_PRICE} Aura", value="nickname_token"
            ))
        return choices[:25]

    @app_commands.command(name="buy", description="Buy an item from the Aura shop")
    @app_commands.describe(item="The item to buy")
    @app_commands.autocomplete(item=_buy_autocomplete)
    async def buy(self, interaction: discord.Interaction, item: str):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        aura_cog = self.bot.get_cog("Aura")
        if not aura_cog:
            await interaction.response.send_message("⚠️ Aura system is not available right now.", ephemeral=True)
            return

        guild_id, user_id = interaction.guild.id, interaction.user.id

        item_type = next((t for t, catalog in CATALOGS.items() if item in catalog), None)
        if item_type:
            catalog = CATALOGS[item_type]
            if self.owns(guild_id, user_id, item_type, item):
                await interaction.response.send_message(f"You already own that {item_type}.", ephemeral=True)
                return
            price = catalog[item]["price"]
            if not aura_cog.remove_balance(guild_id, user_id, price):
                await interaction.response.send_message("You don't have enough Aura for that.", ephemeral=True)
                return
            self.ensure_profile(guild_id, user_id)
            db.connection.execute(
                "INSERT INTO shop_owned_items (guild_id, user_id, item_type, item_id) VALUES (?, ?, ?, ?)",
                (str(guild_id), str(user_id), item_type, item)
            )
            db.connection.commit()
            await interaction.response.send_message(
                f"✅ Purchased the {item_type} **{catalog[item]['name']}** for {price} Aura. Equip it with `/equip`."
            )
            return

        if item == "nickname_token":
            profile = self.ensure_profile(guild_id, user_id)
            if profile["nickname_unlocked"]:
                await interaction.response.send_message("You've already unlocked custom nicknames.", ephemeral=True)
                return
            if not aura_cog.remove_balance(guild_id, user_id, NICKNAME_TOKEN_PRICE):
                await interaction.response.send_message("You don't have enough Aura for that.", ephemeral=True)
                return
            db.connection.execute(
                "UPDATE shop_profile SET nickname_unlocked = 1 WHERE guild_id = ? AND user_id = ?",
                (str(guild_id), str(user_id))
            )
            db.connection.commit()
            await interaction.response.send_message(
                f"✅ Custom nickname unlocked for {NICKNAME_TOKEN_PRICE} Aura. Set it with `/setnickname`."
            )
            return

        await interaction.response.send_message("Unknown item. Use `/shop` to see what's available.", ephemeral=True)

    @app_commands.command(name="inventory", description="Show your owned shop items")
    async def inventory(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        guild_id, user_id = interaction.guild.id, interaction.user.id
        profile = self.ensure_profile(guild_id, user_id)

        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=discord.Color.blue())

        for item_type, label in (("title", "Titles"), ("prefix", "Prefixes"), ("background", "Backgrounds")):
            owned = self.get_owned(guild_id, user_id, item_type)
            equipped = profile[SLOT_COLUMNS[item_type]]
            text = "\n".join(
                f"{'▶️ ' if equipped == item['id'] else ''}{item['name']}"
                for item in CATALOG_LISTS[item_type] if item["id"] in owned
            ) or "None owned"
            embed.add_field(name=label, value=text, inline=False)

        embed.add_field(
            name="Nickname",
            value=(profile["nickname"] or "Not set") if profile["nickname_unlocked"] else "Not unlocked",
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="equip", description="Equip an owned title, prefix, or background (leave item blank to unequip)")
    @app_commands.describe(category="Which slot to change", item="The item to equip")
    @app_commands.choices(category=[
        app_commands.Choice(name="Title", value="title"),
        app_commands.Choice(name="Prefix", value="prefix"),
        app_commands.Choice(name="Background", value="background"),
    ])
    async def equip(self, interaction: discord.Interaction, category: app_commands.Choice[str], item: str = None):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        guild_id, user_id = interaction.guild.id, interaction.user.id
        self.ensure_profile(guild_id, user_id)
        slot_column = SLOT_COLUMNS[category.value]
        catalog = CATALOGS[category.value]

        if item is None:
            db.connection.execute(
                f"UPDATE shop_profile SET {slot_column} = NULL WHERE guild_id = ? AND user_id = ?",
                (str(guild_id), str(user_id))
            )
            db.connection.commit()
            await interaction.response.send_message(f"{category.name} unequipped.", ephemeral=True)
            return

        if not self.owns(guild_id, user_id, category.value, item):
            await interaction.response.send_message(f"You don't own that {category.value}.", ephemeral=True)
            return

        db.connection.execute(
            f"UPDATE shop_profile SET {slot_column} = ? WHERE guild_id = ? AND user_id = ?",
            (item, str(guild_id), str(user_id))
        )
        db.connection.commit()
        await interaction.response.send_message(f"✅ Equipped {category.value} **{catalog[item]['name']}**.", ephemeral=True)

    @equip.autocomplete("item")
    async def equip_item_autocomplete(self, interaction: discord.Interaction, current: str):
        if not interaction.guild:
            return []
        category = getattr(interaction.namespace, "category", None)
        current = current.lower()
        choices = []
        for item_type, catalog_list in CATALOG_LISTS.items():
            if category and category != item_type:
                continue
            owned = self.get_owned(interaction.guild.id, interaction.user.id, item_type)
            for item in catalog_list:
                if item["id"] in owned and current in item["name"].lower():
                    choices.append(app_commands.Choice(name=item["name"], value=item["id"]))
        return choices[:25]

    @app_commands.command(name="setnickname", description="Set your custom profile card nickname (requires the Nickname unlock)")
    @app_commands.describe(text="Your custom nickname")
    async def setnickname(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, MAX_NICKNAME_LENGTH]):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        guild_id, user_id = interaction.guild.id, interaction.user.id
        profile = self.ensure_profile(guild_id, user_id)
        if not profile["nickname_unlocked"]:
            await interaction.response.send_message(
                f"You need to buy the Nickname unlock first (`/buy nickname_token` - {NICKNAME_TOKEN_PRICE} Aura).",
                ephemeral=True
            )
            return
        db.connection.execute(
            "UPDATE shop_profile SET nickname = ? WHERE guild_id = ? AND user_id = ?",
            (text, str(guild_id), str(user_id))
        )
        db.connection.commit()
        await interaction.response.send_message(f"✅ Nickname set to **{text}**.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
