import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="weather", description="Get the weather for a specified location")
    async def weather(self, interaction: discord.Interaction, location: str):
        try:
            api_key = os.getenv('OPENWEATHER_API_KEY')
            if not api_key:
                raise ValueError("OPENWEATHER_API_KEY environment variable not set")
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        weather_description = data['weather'][0]['description']
                        temperature = data['main']['temp']
                        feels_like = data['main']['feels_like']
                        humidity = data['main']['humidity']
                        wind_speed = data['wind']['speed']
                        embed = discord.Embed(
                            title=f"Weather in {location.capitalize()}",
                            description=f"{weather_description.capitalize()}",
                            color=discord.Color.blue()  # Light blue color
                        )
                        embed.add_field(name="Temperature", value=f"{temperature}°C")
                        embed.add_field(name="Feels Like", value=f"{feels_like}°C")
                        embed.add_field(name="Humidity", value=f"{humidity}%")
                        embed.add_field(name="Wind Speed", value=f"{wind_speed} m/s")
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message("Couldn't fetch the weather. Please try again later.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Weather(bot))