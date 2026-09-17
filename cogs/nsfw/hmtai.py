import discord
from discord.ext import commands
from discord import app_commands
import random
import os
import aiohttp

RULE34_API_KEY = os.getenv("RULE34_API_KEY")
RULE34_USER_ID = os.getenv("RULE34_USER_ID")
BASE_URL = "https://api.rule34.xxx/index.php"

CATEGORIES = [
    "anal", "ass", "bdsm", "blowjob", "boobs", "cum",
    "gangbang", "handjob", "masturbation", "neko", "paizuri",
    "piss", "pussy", "tentacle", "thighs", "trap", "waifu",
    "yaoi", "yuri"
]

# Rule34 tags a category to a noisier/broader alias than the one actually
# wanted - "neko" pulls in a lot of unrelated content mistagged by the
# autocomplete tagger, "catgirl" is the tightly-scoped equivalent.
TAG_OVERRIDES = {
    "neko": "catgirl",
}

# AI-generated posts get auto-tagged (rather than tagged by a human curator)
# and are noticeably less accurate, which is the main source of results that
# don't match the requested category - excluding them tightens relevance.
EXCLUDED_TAGS = "-ai_generated -ai_art -ai-created"

class HMTai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] HMTai cog loaded")  # Debug output

    @app_commands.command(name="hentai", description="Get a hentai image from Rule34")
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

        tag = TAG_OVERRIDES.get(category, category)

        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "tags": f"{tag} {EXCLUDED_TAGS}",
            "limit": "100",
            # Randomize which page of results we pull from so repeated calls
            # don't always return the same first 100 posts for a tag.
            "pid": str(random.randint(0, 20)),
            "api_key": RULE34_API_KEY,
            "user_id": RULE34_USER_ID,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(BASE_URL, params=params) as resp:
                    if resp.status != 200:
                        await interaction.response.send_message(
                            f"⚠️ Cannot reach image server for category '{category}'.",
                            ephemeral=True
                        )
                        return

                    posts = await resp.json(content_type=None)
                    posts = [
                        p for p in (posts or [])
                        if p.get("file_url", "").lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
                    ]

                    if not posts:
                        # Random page came up empty (tag has fewer posts than
                        # the pid range covers, or this page was all videos) -
                        # fall back to the first page.
                        params["pid"] = "0"
                        async with session.get(BASE_URL, params=params) as resp2:
                            posts = await resp2.json(content_type=None)
                            posts = [
                                p for p in (posts or [])
                                if p.get("file_url", "").lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
                            ]

                    if not posts:
                        await interaction.response.send_message(
                            f"⚠️ No files found in category '{category}'!", ephemeral=True
                        )
                        return

                    post = random.choice(posts)
                    file_url = post.get("file_url")

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
