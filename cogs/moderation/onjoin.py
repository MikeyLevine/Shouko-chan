import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import os

CONFIG_FILE = "onjoin.json"
OWNER_ID = 1255466299258306611  # Replace with your Discord ID

DEFAULT_EMBED = {
    "title": "✨ Mommy is in the house! ✨",
    "description": (
        "Hi cuties 💕 Shouko-chan just slid into your server, ready to bring chaos and order~\n\n"
        "Here’s what I can do for you:\n\n"
        "🍭 Essentials\n"
        "/automodsetup → Protect your server from spam, links, and naughty words.\n"
        "/warnings → Keep track of rule breakers.\n"
        "/ticketsetup → Create a ticket system for support.\n\n"
        "🎉 Fun & Community\n"
        "/giveaway → Run cool giveaways!\n"
        "/meme, /hentai (don’t ask 👀) → Bring laughs or lewds.\n"
        "/gif → Reaction fun on demand.\n\n"
        "⚙️ Customization\n"
        "Easy setup with slash commands.\n"
        "Only staff control moderation settings.\n"
        "Totally yours—set me up once and I’ll handle the rest.\n\n"
        "💡 Tip: Run /help to see everything I can do\n\n"
        "💬 Need help? Join the support server: [Click here](https://discord.gg/4tp457CRD8)"
    ),
    "footer": "Made with ❤️ by sieln",
    "image_url": "http://192.168.0.15:8080/Shouko/Shouko6.png"
}


class OnJoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        print("[DEBUG] OnJoin cog loaded")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_EMBED, f, indent=4)
            return DEFAULT_EMBED.copy()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Config must be a dictionary")
            return data
        except (json.JSONDecodeError, ValueError):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_EMBED, f, indent=4)
            return DEFAULT_EMBED.copy()

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)
        print("[DEBUG] OnJoin config saved")

    # Event: Bot joins a new guild
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = discord.Embed(
            title=self.config.get("title", DEFAULT_EMBED["title"]),
            description=self.config.get("description", DEFAULT_EMBED["description"]),
            color=discord.Color.blurple()
        )
        if self.config.get("footer"):
            embed.set_footer(text=self.config["footer"])
        if self.config.get("image_url"):
            embed.set_image(url=self.config["image_url"])

        # Send to first text channel bot can send messages in
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(embed=embed)
                break

    # Modal for setup
    class OnJoinSetup(ui.Modal, title="Setup Welcome Embed"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
            self.title_input = ui.TextInput(label="Embed Title", default=DEFAULT_EMBED["title"], required=True)
            self.description_input = ui.TextInput(
                label="Description",
                style=discord.TextStyle.paragraph,
                default=DEFAULT_EMBED["description"],
                required=True,
                max_length=4000
            )
            self.footer_input = ui.TextInput(label="Footer", default=DEFAULT_EMBED["footer"], required=False)
            self.image_url_input = ui.TextInput(label="Image URL", default=DEFAULT_EMBED["image_url"], required=False)
            self.add_item(self.title_input)
            self.add_item(self.description_input)
            self.add_item(self.footer_input)
            self.add_item(self.image_url_input)

        async def on_submit(self, interaction: discord.Interaction):
            # Save temporary values
            self.cog.temp_embed = {
                "title": self.title_input.value,
                "description": self.description_input.value,
                "footer": self.footer_input.value,
                "image_url": self.image_url_input.value
            }
            view = OnJoin.OnJoinButtons(self.cog, interaction.user.id)
            await interaction.response.send_message("Embed configuration ready. Preview or save:", view=view, ephemeral=True)

    # Buttons for Preview / Save
    class OnJoinButtons(ui.View):
        def __init__(self, cog, user_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.user_id = user_id  # Only allow the command user to interact

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Only the setup user can use these buttons.", ephemeral=True)
                return False
            return True

        @ui.button(label="Preview", style=discord.ButtonStyle.blurple)
        async def preview(self, button, interaction: discord.Interaction):
            embed_data = getattr(self.cog, "temp_embed", None)
            if not embed_data:
                await interaction.response.send_message("❌ No embed data to preview!", ephemeral=True)
                return
            embed = discord.Embed(
                title=embed_data.get("title", DEFAULT_EMBED["title"]),
                description=embed_data.get("description", DEFAULT_EMBED["description"]),
                color=discord.Color.green()
            )
            if embed_data.get("footer"):
                embed.set_footer(text=embed_data["footer"])
            if embed_data.get("image_url"):
                embed.set_image(url=embed_data["image_url"])
            # **Respond safely**
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send(embed=embed, ephemeral=True)

        @ui.button(label="Save", style=discord.ButtonStyle.green)
        async def save(self, button, interaction: discord.Interaction):
            embed_data = getattr(self.cog, "temp_embed", None)
            if not embed_data:
                await interaction.response.send_message("❌ Nothing to save!", ephemeral=True)
                return
            self.cog.config = embed_data
            self.cog.save_config()
            # **Respond safely**
            try:
                await interaction.response.send_message("✅ Welcome embed saved! It will now be sent to new servers.", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("✅ Welcome embed saved! It will now be sent to new servers.", ephemeral=True)

    # Command (Owner only)
    @app_commands.command(name="onjoin", description="Setup the default welcome embed (Owner only)")
    async def onjoin(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
            return
        await interaction.response.send_modal(self.OnJoinSetup(self))


async def setup(bot):
    await bot.add_cog(OnJoin(bot))
