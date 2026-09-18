import discord
from discord.ext import commands
from discord import app_commands, ui
import os

import db

OWNER_ROLE_NAMES = ["Admin", "Moderator"]  # Staff roles that can see tickets
TRANSCRIPTS_FOLDER = "data/ticket_transcripts"

if not os.path.exists(TRANSCRIPTS_FOLDER):
    os.makedirs(TRANSCRIPTS_FOLDER)


class TicketButton(ui.View):
    def __init__(self, bot, open_message):
        super().__init__(timeout=None)
        self.bot = bot
        self.open_message = open_message

    @ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        member = interaction.user

        # Prevent duplicate tickets for same user
        existing = db.connection.execute(
            "SELECT channel_id FROM tickets WHERE user_id = ?", (str(member.id),)
        ).fetchone()
        if existing:
            existing_channel = guild.get_channel(int(existing["channel_id"]))
            if existing_channel:
                await interaction.response.send_message(
                    f"You already have an open ticket: {existing_channel.mention}", ephemeral=True
                )
                return

        # Assign ticket number
        ticket_count = db.connection.execute("SELECT COUNT(*) AS c FROM tickets").fetchone()["c"]
        ticket_number = ticket_count + 1
        ticket_name = f"ticket-{ticket_number:03d}"

        # Create category if not exists
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        # Create private channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
        }
        for role in guild.roles:
            if role.name in OWNER_ROLE_NAMES:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            name=ticket_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket opened by {member}"
        )

        # Log ticket
        db.connection.execute(
            "INSERT INTO tickets (channel_id, user_id, guild_id, ticket_number) VALUES (?, ?, ?, ?)",
            (str(ticket_channel.id), str(member.id), str(guild.id), ticket_number)
        )
        db.connection.commit()

        await ticket_channel.send(
            f"Hello {member.mention}! {self.open_message}\nStaff will be with you shortly.\nType `/ticketclose` to close this ticket."
        )
        await interaction.response.send_message(
            f"Ticket created: {ticket_channel.mention}", ephemeral=True
        )


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Ticket cog loaded")

    @app_commands.command(name="ticketsetup", description="Setup the ticket system in this server")
    @app_commands.describe(message="Message to display above the ticket button")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticketsetup(self, interaction: discord.Interaction, message: str):
        category = discord.utils.get(interaction.guild.categories, name="Tickets")
        if not category:
            category = await interaction.guild.create_category("Tickets")

        channel = discord.utils.get(interaction.guild.text_channels, name="open-tickets")
        if not channel:
            channel = await interaction.guild.create_text_channel(
                "open-tickets",
                category=category,
                reason="Ticket system setup"
            )

        view = TicketButton(self.bot, message)
        await channel.send(content=message, view=view)
        await interaction.response.send_message(
            f"Ticket system setup complete in {channel.mention}. Users can now open tickets!", ephemeral=True
        )

    @app_commands.command(name="ticketclose", description="Close this ticket")
    async def ticketclose(self, interaction: discord.Interaction):
        channel = interaction.channel
        row = db.connection.execute(
            "SELECT * FROM tickets WHERE channel_id = ?", (str(channel.id),)
        ).fetchone()

        if not row:
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return

        # Create transcript
        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
        transcript_path = os.path.join(
            TRANSCRIPTS_FOLDER, f"ticket-{row['ticket_number']:03d}.txt"
        )
        with open(transcript_path, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(f"[{msg.created_at}] {msg.author}: {msg.content}\n")

        # Remove ticket from the database
        db.connection.execute("DELETE FROM tickets WHERE channel_id = ?", (str(channel.id),))
        db.connection.commit()

        await interaction.response.send_message(
            f"Ticket closed. Transcript saved: `{transcript_path}`"
        )
        await channel.delete(reason=f"Ticket closed by {interaction.user}")


async def setup(bot):
    await bot.add_cog(Ticket(bot))
