import discord
from discord.ext import commands, tasks
import itertools
import random

class RichPresence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.statuses = itertools.cycle([
            ("playing", "🤖 Use /help for commands"),
            ("playing", "🎉 Invite Shouko-chan to your server!"),
            ("watching", "🌐 {guild_count} servers"),
            ("playing", "🔧 Moderation, fun, and more!"),
            ("watching", "users leveling up 📈"),
            ("playing", "NSFW fun with /reddit 🔞"),
            ("playing", "☁️ Check the weather with /weather"),
            ("watching", "crypto charts 💹 /crypto"),
            ("playing", "Level up in the server!"),
            ("playing", "⚔️ Manage with /kick, /ban, /mute"),
            ("watching", "reaction roles setup"),
            ("playing", "Join us: discord.gg/4tp457CRD8"),
        ])
        self.update_status.start()

    def cog_unload(self):
        self.update_status.cancel()

    @tasks.loop(seconds=30)
    async def update_status(self):
        await self.bot.wait_until_ready()
        kind, text = next(self.statuses)

        text = text.format(guild_count=len(self.bot.guilds))

        if kind == "playing":
            activity = discord.Game(name=text)
        elif kind == "watching":
            activity = discord.Activity(type=discord.ActivityType.watching, name=text)
        else:
            activity = discord.Game(name=text)  # fallback

        await self.bot.change_presence(activity=activity, status=discord.Status.online)

    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RichPresence(bot))
