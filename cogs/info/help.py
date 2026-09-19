import discord
from discord.ext import commands
from discord import app_commands

OWNER_ID = 1255466299258306611

# A handful of commands gate themselves with a manual
# `if interaction.user.id != OWNER_ID` check in the function body instead
# of a decorator (cogs/owner/shutdown.py, cogs/games/giveaway.py,
# cogs/settings/server_command.py, cogs/utility/onjoin.py, main.py's
# /reload) - those don't show up in a command's .checks list, so they
# can't be detected automatically like the decorator-based ones can.
# Checked every file referencing OWNER_ID/AUTHORIZED_USER_ID to build this.
MANUALLY_OWNER_GATED = {"shutdown", "giveaway", "server", "reload", "onjoin"}

CATEGORY_ORDER = ["economy", "profile", "games", "general", "moderation", "settings", "utility", "info", "nsfw", "owner"]
CATEGORY_LABELS = {
    "economy": "💰 Economy",
    "profile": "🖼️ Profile & Customization",
    "games": "🎲 Games",
    "general": "🎉 General",
    "moderation": "🛡️ Moderation",
    "settings": "⚙️ Settings",
    "utility": "🔧 Utility",
    "info": "ℹ️ Info",
    "nsfw": "🔞 NSFW",
    "owner": "👑 Owner Only",
}


def _is_owner_only(command):
    if command.name in MANUALLY_OWNER_GATED:
        return True
    for check in command.checks:
        func = getattr(check, "__func__", check)  # unwrap a staticmethod, if it is one
        if getattr(func, "__name__", "") == "is_owner":
            return True
    return False


def _category_for(command):
    if command.binding is None:
        # A bare bot.tree.command with no cog (e.g. main.py's /reload) -
        # the only one of these right now is owner-only anyway.
        return "owner"
    module_parts = type(command.binding).__module__.split(".")
    if len(module_parts) >= 2 and module_parts[0] == "cogs":
        return module_parts[1]
    return "general"


def _build_categories(bot, requesting_user_id):
    categories = {}
    for command in bot.tree.walk_commands():
        if _is_owner_only(command) and requesting_user_id != OWNER_ID:
            continue
        key = _category_for(command)
        if _is_owner_only(command):
            key = "owner"
        categories.setdefault(key, []).append(command)
    for key in categories:
        categories[key].sort(key=lambda c: c.name)
    return categories


def _category_embed(key, commands_list):
    lines = [f"**/{c.name}** — {c.description or 'No description provided'}" for c in commands_list]
    embed = discord.Embed(
        title=CATEGORY_LABELS.get(key, key.capitalize()),
        description="\n".join(lines),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"{len(commands_list)} command{'s' if len(commands_list) != 1 else ''}")
    return embed


class CategorySelect(discord.ui.Select):
    def __init__(self, categories, user_id):
        self.categories = categories
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label=CATEGORY_LABELS.get(key, key.capitalize()),
                value=key,
                description=f"{len(categories[key])} command{'s' if len(categories[key]) != 1 else ''}"
            )
            for key in CATEGORY_ORDER if key in categories
        ]
        super().__init__(placeholder="Choose a category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your help menu.", ephemeral=True)
            return
        key = self.values[0]
        await interaction.response.edit_message(embed=_category_embed(key, self.categories[key]), view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, categories, user_id):
        super().__init__(timeout=120)
        self.add_item(CategorySelect(categories, user_id))


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Help cog loaded")  # Debug output when cog loads

    @app_commands.command(name="help", description="Browse all commands by category")
    async def help(self, interaction: discord.Interaction):
        categories = _build_categories(self.bot, interaction.user.id)
        total = sum(len(cmds) for cmds in categories.values())

        overview_lines = [
            f"{CATEGORY_LABELS.get(key, key.capitalize())} — {len(categories[key])}"
            for key in CATEGORY_ORDER if key in categories
        ]
        embed = discord.Embed(
            title="Shouko-chan Help",
            description=f"{total} commands across {len(categories)} categories. Pick one below to see what's in it.\n\n"
                        + "\n".join(overview_lines),
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed, view=HelpView(categories, interaction.user.id), ephemeral=True)
        print(f"[DEBUG] Help command shown to {interaction.user}")

async def setup(bot):
    await bot.add_cog(Help(bot))
