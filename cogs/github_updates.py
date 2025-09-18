# cogs/github_updates.py
import discord
from discord.ext import commands, tasks
from discord import app_commands
from aiohttp import web
import json

GITHUB_CHANNEL_ID = 1418221499466121408  # Discord channel to post commits
WEBHOOK_PORT = 8081  # port for the bot HTTP server
WEBHOOK_PATH = "/github-webhook"  # endpoint GitHub will post to

class GitHubUpdates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.runner = None
        self.site = None
        self.bot.loop.create_task(self.start_server())

    async def start_server(self):
        app = web.Application()
        app.router.add_post(WEBHOOK_PATH, self.handle_webhook)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "0.0.0.0", WEBHOOK_PORT)
        await self.site.start()
        print(f"[DEBUG] GitHub webhook server running at http://0.0.0.0:{WEBHOOK_PORT}{WEBHOOK_PATH}")

    async def handle_webhook(self, request):
        try:
            data = await request.json()
        except Exception as e:
            return web.Response(text="Invalid JSON", status=400)

        # Only handle push events
        if request.headers.get("X-GitHub-Event") != "push":
            return web.Response(text="Ignored", status=200)

        commits = data.get("commits", [])
        repo_name = data.get("repository", {}).get("full_name", "Unknown repo")
        pusher = data.get("pusher", {}).get("name", "Unknown user")

        channel = self.bot.get_channel(GITHUB_CHANNEL_ID)
        if not channel:
            return web.Response(text="Channel not found", status=500)

        for commit in commits:
            msg = commit.get("message", "")
            url = commit.get("url", "")
            author = commit.get("author", {}).get("name", "Unknown")
            embed = discord.Embed(
                title=f"New commit in {repo_name}",
                description=f"**Author:** {author}\n**Pusher:** {pusher}\n**Message:** {msg}\n[View Commit]({url})",
                color=discord.Color.blue()
            )
            await channel.send(embed=embed)

        return web.Response(text="OK", status=200)

async def setup(bot):
    await bot.add_cog(GitHubUpdates(bot))
