import discord
from discord.ext import commands, tasks
from discord import app_commands
import time

import db

OWNER_ID = 1255466299258306611  # Your Discord ID

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Giveaway cog loaded")
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

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

        db.connection.execute(
            "INSERT INTO giveaways (message_id, guild_id, channel_id, prize, host_id, end_time) VALUES (?, ?, ?, ?, ?, ?)",
            (str(message.id), str(interaction.guild.id), str(interaction.channel.id), prize, str(interaction.user.id), end_time)
        )
        db.connection.commit()
        await interaction.response.send_message(f"Giveaway started for **{prize}**!", ephemeral=True)

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        now = int(time.time())
        rows = db.connection.execute("SELECT * FROM giveaways WHERE end_time <= ?", (now,)).fetchall()

        for row in rows:
            guild = self.bot.get_guild(int(row["guild_id"]))
            if guild:
                channel = guild.get_channel(int(row["channel_id"]))
                try:
                    message = await channel.fetch_message(int(row["message_id"]))
                    users = []
                    for reaction in message.reactions:
                        if str(reaction.emoji) == "🎉":
                            async for user in reaction.users():
                                if not user.bot:
                                    users.append(user)
                    if users:
                        winner = self.bot.get_user(users[0].id) if users else None
                        if winner:
                            await channel.send(f"🎉 Congratulations {winner.mention}! You won **{row['prize']}**!")
                        else:
                            await channel.send(f"No valid participants for **{row['prize']}**.")
                    else:
                        await channel.send(f"No participants for **{row['prize']}**.")
                except discord.NotFound:
                    pass

            db.connection.execute("DELETE FROM giveaways WHERE message_id = ?", (row["message_id"],))

        if rows:
            db.connection.commit()

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
