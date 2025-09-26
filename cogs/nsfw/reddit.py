import discord
from discord.ext import commands
from discord import app_commands
import asyncpraw
import os

class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Reddit cog loaded")  # Debug output

    @app_commands.command(
        name="reddit",
        description="Fetch NSFW posts from Reddit"
    )
    @app_commands.describe(
        subreddit="The subreddit to fetch posts from",
        sort="The sorting method for posts"
    )
    @app_commands.choices(sort=[
        app_commands.Choice(name="Hot", value="hot"),
        app_commands.Choice(name="New", value="new"),
        app_commands.Choice(name="Top", value="top"),
        app_commands.Choice(name="Controversial", value="controversial")
    ])
    async def reddit(
        self,
        interaction: discord.Interaction,
        subreddit: str,
        sort: app_commands.Choice[str]
    ):
        try:
            client_id = os.getenv('REDDIT_CLIENT_ID')
            client_secret = os.getenv('REDDIT_CLIENT_SECRET')
            user_agent = os.getenv('REDDIT_USER_AGENT')

            print(f"[DEBUG] Reddit command invoked: subreddit={subreddit}, sort={sort.value}, user={interaction.user}")

            if not client_id or not client_secret or not user_agent:
                await interaction.response.send_message(
                    "Reddit API credentials are not set.", ephemeral=True
                )
                print("[DEBUG] Reddit API credentials missing")
                return

            reddit = asyncpraw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )

            subreddit_obj = await reddit.subreddit(subreddit)
            posts = []

            fetch_limit = 5
            async for submission in getattr(subreddit_obj, sort.value)(limit=fetch_limit):
                if submission.over_18:
                    embed = discord.Embed(
                        title=submission.title,
                        url=submission.url,
                        color=discord.Color.red()
                    )
                    # If the post is an image
                    if submission.url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        embed.set_image(url=submission.url)
                    # If the post is a video (Reddit hosted)
                    elif hasattr(submission, "media") and submission.media and "reddit_video" in submission.media:
                        video_url = submission.media["reddit_video"]["fallback_url"]
                        embed.add_field(name="Video", value=f"[Watch Video]({video_url})", inline=False)
                    else:
                        embed.add_field(name="Link", value=submission.url, inline=False)
                    embed.set_footer(text=f"r/{subreddit} | 👍 {submission.score} | 💬 {submission.num_comments}")
                    await interaction.channel.send(embed=embed)
                    posts.append(f"Title: {submission.title}\nURL: {submission.url}")

            if posts:
                await interaction.response.send_message('\n\n'.join(posts))
                print(f"[DEBUG] Sent {len(posts)} NSFW posts from r/{subreddit}")
            else:
                await interaction.response.send_message("No NSFW posts found.", ephemeral=True)
                print(f"[DEBUG] No NSFW posts found in r/{subreddit}")

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            print(f"[ERROR] Reddit command error: {e}")

# ✅ Correct setup function
async def setup(bot):
    await bot.add_cog(Reddit(bot))
