import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import json
import os
import time

GIVEAWAYS_FILE = "data/giveaways.json"
OWNER_ID = 1255466299258306611  # Your Discord ID

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Giveaway cog loaded")
        self.load_giveaways()
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    def load_giveaways(self):
        if os.path.exists(GIVEAWAYS_FILE):
            with open(GIVEAWAYS_FILE, "r", encoding="utf-8") as f:
                self.giveaways = json.load(f)
        else:
            self.giveaways = {}

    def save_giveaways(self):
        with open(GIVEAWAYS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.giveaways, f, indent=4, ensure_ascii=False)

    @app_commands.command(name="giveaway", description="Create a giveaway")
    @app_commands.describe(prize="The prize to give away", duration="Duration in minutes")
    async def giveaway(self, interaction: discord.Interaction, prize: str, duration: int):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("Only the bot owner can create giveaways.", ephemeral=True)
            return

        end_time = int(time.time()) + duration * 60

        embed = discord.Embed(
            title="🎉 Giveaway! 🎉",
            description=f"Prize: **{prize}**\nReact with 🎉 to enter!\nEnds in {duration} minutes.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Hosted by {interaction.user}")

        message = await interaction.channel.send(embed=embed)
        await message.add_reaction("🎉")

        # Save giveaway
        self.giveaways[str(message.id)] = {
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "prize": prize,
            "host": interaction.user.id,
            "end_time": end_time,
            "participants": []
        }
        self.save_giveaways()
        await interaction.response.send_message(f"Giveaway started for **{prize}**!", ephemeral=True)

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        now = int(time.time())
        ended = []

        for message_id, data in self.giveaways.items():
            if now >= data["end_time"]:
                guild = self.bot.get_guild(data["guild_id"])
                channel = guild.get_channel(data["channel_id"])
                try:
                    message = await channel.fetch_message(int(message_id))
                    users = []
                    for reaction in message.reactions:
                        if str(reaction.emoji) == "🎉":
                            async for user in reaction.users():
                                if not user.bot:
                                    users.append(user)
                    if users:
                        winner = self.bot.get_user(users[0].id) if users else None
                        if winner:
                            await channel.send(f"🎉 Congratulations {winner.mention}! You won **{data['prize']}**!")
                        else:
                            await channel.send(f"No valid participants for **{data['prize']}**.")
                    else:
                        await channel.send(f"No participants for **{data['prize']}**.")
                except discord.NotFound:
                    pass

                ended.append(message_id)

        # Remove ended giveaways
        for mid in ended:
            del self.giveaways[mid]

        if ended:
            self.save_giveaways()

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
