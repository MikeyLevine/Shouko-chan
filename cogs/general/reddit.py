import discord
from discord.ext import commands
from discord import app_commands
import asyncpraw
import os

class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reddit", description="Fetch NSFW posts from Reddit")
    @app_commands.describe(subreddit="The subreddit to fetch posts from", sort="The sorting method for posts")
    @app_commands.choices(sort=[
        app_commands.Choice(name="Hot", value="hot"),
        app_commands.Choice(name="New", value="new"),
        app_commands.Choice(name="Top", value="top"),
        app_commands.Choice(name="Controversial", value="controversial")
    ])
    async def reddit(self, interaction: discord.Interaction, subreddit: str, sort: app_commands.Choice[str]):
        try:
            client_id = os.getenv('REDDIT_CLIENT_ID')
            client_secret = os.getenv('REDDIT_CLIENT_SECRET')
            user_agent = os.getenv('REDDIT_USER_AGENT')

            if not client_id or not client_secret or not user_agent:
                await interaction.response.send_message("Reddit API credentials are not set.")
                return

            # Use asyncpraw to interact with Reddit
            reddit = asyncpraw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )

            subreddit_obj = await reddit.subreddit(subreddit)
            posts = []

            if sort.value == "hot":
                async for submission in subreddit_obj.hot(limit=5):
                    if submission.over_18:
                        posts.append(f"Title: {submission.title}\nURL: {submission.url}")
            elif sort.value == "new":
                async for submission in subreddit_obj.new(limit=5):
                    if submission.over_18:
                        posts.append(f"Title: {submission.title}\nURL: {submission.url}")
            elif sort.value == "top":
                async for submission in subreddit_obj.top(limit=5):
                    if submission.over_18:
                        posts.append(f"Title: {submission.title}\nURL: {submission.url}")
            elif sort.value == "controversial":
                async for submission in subreddit_obj.controversial(limit=5):
                    if submission.over_18:
                        posts.append(f"Title: {submission.title}\nURL: {submission.url}")

            if posts:
                await interaction.response.send_message('\n\n'.join(posts))
            else:
                await interaction.response.send_message("No NSFW posts found.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Reddit(bot))