import discord
from discord.ext import commands
from discord import app_commands
import random

class EightBall(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="Your question for the 8-ball")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        """Ask the magic 8-ball a question and get a random response."""
        
        # List of possible responses
        responses = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes - definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."
        ]
        
        # Select a random response
        response = random.choice(responses)
        
        # Create an embed for the response
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            description=f"**Question:** {question}\n\n**Answer:** {response}",
            color=discord.Color.blue()
        )
        
        # Send the embed
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EightBall(bot))
