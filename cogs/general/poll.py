import discord
from discord.ext import commands
from discord import app_commands

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="poll", description="Create a poll with up to 4 options. Provide a question and up to 4 options for users to vote on.")
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None):
        embed = discord.Embed(title="Poll", description=question, color=discord.Color.blue())
        
        options = [option1, option2, option3, option4]
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        
        for i, option in enumerate(options):
            if option:
                embed.add_field(name=f"{emojis[i]} {option}", value="\u200b", inline=False)

        await interaction.response.send_message(embed=embed)
        poll_message = await interaction.original_response()

        for i, option in enumerate(options):
            if option:
                await poll_message.add_reaction(emojis[i])

async def setup(bot):
    await bot.add_cog(Poll(bot))