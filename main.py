import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
import asyncio

load_dotenv()

with open('config.json', 'r') as f:
    config = json.load(f)
prefix = config.get('prefix', '!')
welcome_message = config.get('welcome_message', 'Welcome to the server, {member}!')
goodbye_message = config.get('goodbye_message', 'Goodbye, {member}. We will miss you!')
log_channel_id = config.get('log_channel_id')
welcome_channel_id = config.get('welcome_channel_id')
announcement_channel_id = config.get('announcement_channel_id')

token = os.getenv('TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=prefix, intents=intents)

cogs = [
    'cogs.general.hello',
    'cogs.general.ping',
    'cogs.general.poll',
    'cogs.general.jokes',
    'cogs.moderation.moderation',
    'cogs.logging',
    'cogs.general.weather',
    'cogs.general.crypto',
    'cogs.general.inandout',
    'cogs.general.help',  # Ensure this line is present to load the help cog
    'cogs.general.reaction_roles',
    # 'cogs.general.richpresence',  # Comment out this line to disable richpresence
    'cogs.general.hmtai',
    'cogs.general.shutdown',
    'cogs.general.welcome',
    'cogs.general.embed',
    'cogs.general.membercount',
    'cogs.general.warnings',
    'cogs.general.afk',
    'cogs.general.invite',  # Add this line to load the invite cog
    'cogs.general.leveling',  # Add this line to load the leveling cog
    'cogs.general.owner_commands',  # Add this line to load the owner commands cog
    'cogs.general.setupdm'  # Add this line to load the setupdm cog
]

@bot.event
async def on_ready():
    if not hasattr(bot, 'ready'):
        bot.ready = True
        print(f'Logged on as {bot.user}!')
        loaded_cogs = []
        failed_cogs = []

        for cog in cogs:
            try:
                await bot.load_extension(cog)
                loaded_cogs.append(cog)
            except Exception as e:
                failed_cogs.append((cog, str(e)))
                print(f"Failed to load cog {cog}: {e}")

        print("\nSummary of Cog Loading:")
        print(f"Successfully loaded cogs: {', '.join(loaded_cogs)}")
        if failed_cogs:
            print("Failed to load the following cogs:")
            for cog, error in failed_cogs:
                print(f"{cog}: {error}")

        try:
            synced = await bot.tree.sync()
            print(f'Synced {len(synced)} slash commands')
        except Exception as e:
            print(f'Failed to sync slash commands: {e}')
        
        print("All commands loaded successfully!")

@bot.event
async def on_member_join(member):
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            await channel.send(welcome_message.format(member=member.mention))
    if announcement_channel_id:
        channel = bot.get_channel(announcement_channel_id)
        if channel:
            await channel.send(f"{member.mention} has joined the server!")

@bot.event
async def on_member_remove(member):
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            await channel.send(goodbye_message.format(member=member.mention))

async def main():
    try:
        async with bot:
            await bot.start(token)
    except KeyboardInterrupt:
        print("Bot is shutting down...")
        await bot.close()
    finally:
        print("Cleaning up...")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

asyncio.run(main())