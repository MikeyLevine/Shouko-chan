import discord
from discord.ext import commands
from discord import app_commands
import random
import os
import aiohttp

RULE34_API_KEY = os.getenv("RULE34_API_KEY")
RULE34_USER_ID = os.getenv("RULE34_USER_ID")
RULE34_BASE_URL = "https://api.rule34.xxx/index.php"
NEKOBOT_BASE_URL = "https://nekobot.xyz/api/image"

CATEGORIES = [
    "anal", "ass", "bdsm", "blowjob", "boobs", "cum",
    "gangbang", "handjob", "masturbation", "neko", "paizuri",
    "piss", "pussy", "tentacle", "thighs", "trap", "waifu",
    "yaoi", "yuri"
]

# Nekobot is a small hand-picked category set rather than crowd-tagged, so
# it's noticeably more accurate where it has a matching category. It only
# covers about half our categories though - everything else (bdsm, cum,
# gangbang, handjob, masturbation, piss, trap, waifu) falls through to
# Rule34, and any nekobot failure also falls back to Rule34.
NEKOBOT_TYPE_MAP = {
    "anal": "hanal",
    "ass": "hass",
    "boobs": "hboobs",
    "neko": "hneko",
    "paizuri": "paizuri",
    "pussy": "pussy",
    "tentacle": "tentacle",
    "thighs": "hthigh",
    "yaoi": "yaoi",
    "yuri": "hyuri",
    "blowjob": "blowjob",
}

# Rule34 tags a category to a noisier/broader alias than the one actually
# wanted - "neko" pulls in a lot of unrelated content mistagged by the
# autocomplete tagger, "catgirl" is the tightly-scoped equivalent.
RULE34_TAG_OVERRIDES = {
    "neko": "catgirl",
}

# AI-generated posts get auto-tagged (rather than tagged by a human curator)
# and are noticeably less accurate, which is the main source of results that
# don't match the requested category - excluding them tightens relevance.
RULE34_EXCLUDED_TAGS = "-ai_generated -ai_art -ai-created"

# Higher-scored posts get more community eyes on them, so bad/mismatched
# tags are more likely to have been caught and fixed. 200 was checked
# against all 19 categories and still returns a full pool for each.
RULE34_MIN_SCORE = "score:>=200"


async def get_nekobot_image(session, nekobot_type):
    try:
        async with session.get(NEKOBOT_BASE_URL, params={"type": nekobot_type}) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
            if not data.get("success"):
                return None
            return data.get("message")
    except aiohttp.ClientError:
        return None


async def get_rule34_image(session, category):
    tag = RULE34_TAG_OVERRIDES.get(category, category)
    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": "1",
        "tags": f"{tag} {RULE34_EXCLUDED_TAGS} {RULE34_MIN_SCORE}",
        "limit": "100",
        # Randomize which page of results we pull from so repeated calls
        # don't always return the same first 100 posts for a tag.
        "pid": str(random.randint(0, 20)),
        "api_key": RULE34_API_KEY,
        "user_id": RULE34_USER_ID,
    }

    async def fetch(pid):
        params["pid"] = pid
        async with session.get(RULE34_BASE_URL, params=params) as resp:
            if resp.status != 200:
                return []
            posts = await resp.json(content_type=None)
            return [
                p for p in (posts or [])
                if p.get("file_url", "").lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]

    posts = await fetch(str(random.randint(0, 20)))
    if not posts:
        # Random page came up empty (tag has fewer posts than the pid range
        # covers, or this page was all videos) - fall back to the first page.
        posts = await fetch("0")

    if not posts:
        return None

    return random.choice(posts).get("file_url")


class HMTai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] HMTai cog loaded")  # Debug output

    @app_commands.command(name="hentai", description="Get a hentai image")
    async def hentai(self, interaction: discord.Interaction, category: str):
        category = category.lower()
        if category not in CATEGORIES:
            await interaction.response.send_message(
                f"❌ Invalid category '{category}'.\nAvailable: {', '.join(CATEGORIES)}",
                ephemeral=True
            )
            return

        if not RULE34_API_KEY or not RULE34_USER_ID:
            await interaction.response.send_message(
                "⚠️ Rule34 API credentials are not set.", ephemeral=True
            )
            return

        try:
            async with aiohttp.ClientSession() as session:
                file_url = None

                nekobot_type = NEKOBOT_TYPE_MAP.get(category)
                if nekobot_type:
                    file_url = await get_nekobot_image(session, nekobot_type)

                if not file_url:
                    file_url = await get_rule34_image(session, category)

                if not file_url:
                    await interaction.response.send_message(
                        f"⚠️ No files found in category '{category}'!", ephemeral=True
                    )
                    return

        except aiohttp.ClientError as e:
            await interaction.response.send_message(f"❌ HTTP error: {e}", ephemeral=True)
            print(f"[ERROR] HTTP error in HMTai: {e}")
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Unexpected error: {e}", ephemeral=True)
            print(f"[ERROR] Unexpected in HMTai: {e}")
            return

        embed = discord.Embed(
            title=f"Hentai - {category.capitalize()}",
            color=discord.Color.red()
        )
        embed.set_image(url=file_url)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(HMTai(bot))
