import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
import asyncio
from discord import app_commands

load_dotenv()

with open('data/config.json', 'r') as f:
    config = json.load(f)
prefix = config.get('prefix', '!')
welcome_message = config.get('welcome_message', 'Welcome to the server, {member}!')
goodbye_message = config.get('goodbye_message', 'Goodbye, {member}. We will miss you!')
log_channel_id = config.get('log_channel_id')
welcome_channel_id = config.get('welcome_channel_id')
announcement_channel_id = config.get('announcement_channel_id')

token = os.getenv('TOKEN')
owner_id = int(os.getenv("OWNER_ID", 0))  # Set your Discord ID in .env

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=prefix, intents=intents)

cogs = [
    # General commands
    'cogs.general.react',
    'cogs.general.roll',
    'cogs.general.flip',
    'cogs.general.8ball',
    'cogs.general.embed',
    'cogs.general.hello',
    'cogs.general.membercount',
    'cogs.general.ping',
    'cogs.general.poll',
    'cogs.general.reaction_roles',
    'cogs.general.welcome',
    
    # Moderation commands
    'cogs.moderation.automod',
    'cogs.moderation.moderation',
    'cogs.moderation.warnings',
    
    # Games commands
    'cogs.games.giveaway',
    'cogs.games.rps',
    'cogs.games.trivia',

    # Info commands
    'cogs.info.help',
    'cogs.info.invite',

    # NSFW commands
    'cogs.nsfw.hmtai',
    'cogs.nsfw.reddit',
    
    # Owner commands
    'cogs.owner.owner_commands',
    'cogs.owner.shutdown',

    # Settings commands
    'cogs.settings.inandout',
    'cogs.settings.leveling',
    'cogs.settings.setupdm',
    'cogs.settings.server_command',
    'cogs.settings.server_notify',

    # Utility commands
    'cogs.utility.afk',
    'cogs.utility.crypto',
    'cogs.utility.jokes',
    'cogs.utility.onjoin',
    'cogs.utility.richpresence',
    'cogs.utility.ticket',
    'cogs.utility.weather',
    
    # Standalone files
    'cogs.logging'
]

@bot.event
async def on_ready():
    if not hasattr(bot, 'ready'):
        bot.ready = True
        print(f'Logged on as {bot.user}!')

        # Load all cogs; each cog will print its own debug message
        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f"[COG LOADED] {cog}")
            except Exception as e:
                print(f"[ERROR] Failed to load cog {cog}: {e}")

        # Sync slash commands
        try:
            await bot.tree.sync()
            print(f"[DEBUG] Slash commands synced.")
        except Exception as e:
            print(f"[ERROR] Failed to sync slash commands: {e}")


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


# 🔄 Reload command for cogs
@bot.tree.command(name="reload", description="Reload a specific cog")
@app_commands.describe(cog_name="The full path of the cog (e.g., cogs.general.ping)")
async def reload(interaction: discord.Interaction, cog_name: str):
    if interaction.user.id != owner_id:
        await interaction.response.send_message("❌ You don’t have permission to reload cogs.", ephemeral=True)
        return

    if cog_name not in cogs:
        await interaction.response.send_message(f"❌ Cog {cog_name} not found in cogs list.", ephemeral=True)
        return

    try:
        await bot.unload_extension(cog_name)
        await bot.load_extension(cog_name)
        await interaction.response.send_message(f"✅ Reloaded {cog_name} successfully.", ephemeral=True)
        print(f"[RELOAD] {cog_name} reloaded by {interaction.user}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to reload {cog_name}: {e}", ephemeral=True)
        print(f"[ERROR] Failed to reload {cog_name}: {e}")


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
