import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import os

TICKETS_FILE = "tickets.json"
OWNER_ROLE_NAMES = ["Admin", "Moderator"]  # Staff roles that can see tickets
TRANSCRIPTS_FOLDER = "ticket_transcripts"

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

        # Load tickets JSON
        tickets = {}
        if os.path.exists(TICKETS_FILE):
            with open(TICKETS_FILE, "r") as f:
                tickets = json.load(f)

        # Assign ticket number
        ticket_number = len(tickets) + 1
        ticket_name = f"ticket-{ticket_number:03d}"

        # Prevent duplicate tickets for same user
        for t_id, t_info in tickets.items():
            if t_info["user_id"] == member.id:
                existing_channel = guild.get_channel(int(t_id))
                if existing_channel:
                    await interaction.response.send_message(
                        f"You already have an open ticket: {existing_channel.mention}", ephemeral=True
                    )
                    return

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
        tickets[str(ticket_channel.id)] = {
            "user_id": member.id,
            "guild_id": guild.id,
            "ticket_number": ticket_number
        }
        with open(TICKETS_FILE, "w") as f:
            json.dump(tickets, f, indent=4)

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
        if not os.path.exists(TICKETS_FILE):
            await interaction.response.send_message("No tickets found.", ephemeral=True)
            return

        with open(TICKETS_FILE, "r") as f:
            tickets = json.load(f)

        if str(channel.id) not in tickets:
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return

        ticket_info = tickets[str(channel.id)]

        # Create transcript
        messages = await channel.history(limit=None, oldest_first=True).flatten()
        transcript_path = os.path.join(
            TRANSCRIPTS_FOLDER, f"ticket-{ticket_info['ticket_number']:03d}.txt"
        )
        with open(transcript_path, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(f"[{msg.created_at}] {msg.author}: {msg.content}\n")

        # Remove ticket from JSON
        del tickets[str(channel.id)]
        with open(TICKETS_FILE, "w") as f:
            json.dump(tickets, f, indent=4)

        await interaction.response.send_message(
            f"Ticket closed. Transcript saved: `{transcript_path}`"
        )
        await channel.delete(reason=f"Ticket closed by {interaction.user}")


async def setup(bot):
    await bot.add_cog(Ticket(bot))

