import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import aiohttp
import random
import urllib.parse
import traceback

class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/trivia.json"
        self.sessions_file = "data/trivia_sessions.json"
        self.active_sessions = {}  # {channel_id: session_data}
        self.data = {"global_leaderboard": {}, "server_leaderboards": {}}
        self.session_token = os.getenv("OPENTDB_TOKEN")  # Optional token

        os.makedirs("data", exist_ok=True)
        self.load_data()
        self.load_sessions()
        print("[DEBUG] Trivia cog loaded")

    # ------------------- JSON Handling -------------------
    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    self.data = json.load(f)
                print("[DEBUG] Trivia leaderboard loaded")
            else:
                self.save_data()
        except Exception as e:
            print(f"[ERROR] Failed to load trivia data: {e}")
            traceback.print_exc()

    def save_data(self):
        try:
            with open(self.data_file, "w") as f:
                json.dump(self.data, f)
            print("[DEBUG] Trivia leaderboard saved")
        except Exception as e:
            print(f"[ERROR] Failed to save trivia data: {e}")
            traceback.print_exc()

    def load_sessions(self):
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, "r") as f:
                    self.active_sessions = json.load(f)
                print("[DEBUG] Trivia sessions loaded")
            except Exception:
                print("[WARNING] trivia_sessions.json is corrupted. Starting with empty sessions.")
                self.active_sessions = {}
        else:
            self.save_sessions()

    def save_sessions(self):
        try:
            # Only save persistent data (no live objects like message or interaction)
            data_to_save = {}
            for cid, session in self.active_sessions.items():
                data_to_save[cid] = {
                    "question": session.get("question"),
                    "players": session.get("players", {}),
                    "category": session.get("category"),
                    "message_id": session.get("message").id if session.get("message") else None,
                    "channel_id": session.get("message").channel.id if session.get("message") else None
                }
            with open(self.sessions_file, "w") as f:
                json.dump(data_to_save, f)
            print("[DEBUG] Trivia sessions saved")
        except Exception as e:
            print(f"[ERROR] Failed to save trivia sessions: {e}")
            traceback.print_exc()

    # ------------------- OpenTDB API -------------------
    async def get_session_token(self):
        try:
            if self.session_token:
                return self.session_token
            async with aiohttp.ClientSession() as session:
                async with session.get("https://opentdb.com/api_token.php?command=request") as resp:
                    data = await resp.json()
            self.session_token = data.get("token")
            print(f"[DEBUG] New OpenTDB session token: {self.session_token}")
            return self.session_token
        except Exception as e:
            print(f"[ERROR] Failed to get OpenTDB token: {e}")
            traceback.print_exc()
            return None

    async def fetch_question(self, category_id=None):
        try:
            token = await self.get_session_token()
            url = f"https://opentdb.com/api.php?amount=1&type=multiple&encode=url3986"
            if category_id:
                url += f"&category={category_id}"
            if token:
                url += f"&token={token}"

            print(f"[DEBUG] Fetching question from URL: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()

            code = data.get("response_code")
            if code == 0:
                q = data["results"][0]
                answers = q["incorrect_answers"] + [q["correct_answer"]]
                random.shuffle(answers)
                question = {
                    "question": urllib.parse.unquote(q["question"]),
                    "answers": [urllib.parse.unquote(a) for a in answers],
                    "correct": urllib.parse.unquote(q["correct_answer"])
                }
                print(f"[DEBUG] Question fetched: {question}")
                return question
            elif code in [3, 4]:
                print(f"[DEBUG] Token issue detected (code {code}), resetting token.")
                self.session_token = None
                return await self.fetch_question(category_id)
            else:
                print(f"[ERROR] OpenTDB returned response code: {code}")
                return None
        except Exception as e:
            print(f"[ERROR] Failed to fetch trivia question: {e}")
            traceback.print_exc()
            return None

    # ------------------- Button Class -------------------
    class AnswerButton(discord.ui.Button):
        def __init__(self, label, trivia_cog, answer):
            super().__init__(label=label, style=discord.ButtonStyle.primary)
            self.trivia_cog = trivia_cog
            self.answer = answer

        async def callback(self, interaction: discord.Interaction):
            try:
                cid = str(interaction.channel_id)
                session = self.trivia_cog.active_sessions.get(cid)
                if not session:
                    await interaction.response.send_message("This session has ended.", ephemeral=True)
                    return

                user_id = str(interaction.user.id)
                if user_id in session["players"]:
                    await interaction.response.send_message("You already answered this question!", ephemeral=True)
                    return

                correct = session["question"]["correct"]
                if self.answer == correct:
                    session["players"][user_id] = 1
                    await interaction.response.send_message("✅ Correct!", ephemeral=True)
                else:
                    session["players"][user_id] = 0
                    await interaction.response.send_message(f"❌ Wrong! The correct answer was **{correct}**", ephemeral=True)

                # update leaderboard immediately
                self.trivia_cog.update_leaderboard(interaction.guild_id, user_id, session["players"][user_id])

                # reset players for next question
                session["players"] = {}

                # send next question
                await self.trivia_cog.next_question(cid)
            except Exception as e:
                print(f"[ERROR] AnswerButton callback error: {e}")
                traceback.print_exc()
                await interaction.response.send_message("❌ An error occurred while processing your answer.", ephemeral=True)

    # ------------------- Leaderboard -------------------
    def update_leaderboard(self, guild_id, user_id, win):
        try:
            gl = self.data["global_leaderboard"]
            if user_id not in gl:
                gl[user_id] = {"wins": 0, "games_played": 0}
            gl[user_id]["games_played"] += 1
            gl[user_id]["wins"] += win

            sid = str(guild_id)
            sl = self.data["server_leaderboards"].setdefault(sid, {})
            if user_id not in sl:
                sl[user_id] = {"wins": 0, "games_played": 0}
            sl[user_id]["games_played"] += 1
            sl[user_id]["wins"] += win

            self.save_data()
        except Exception as e:
            print(f"[ERROR] Failed to update leaderboard: {e}")
            traceback.print_exc()

    # ------------------- Next Question -------------------
    async def next_question(self, channel_id):
        session = self.active_sessions.get(channel_id)
        if not session:
            return

        category = session.get("category")
        question = await self.fetch_question(category)
        if not question:
            return

        session["question"] = question
        self.save_sessions()

        embed = discord.Embed(title="Trivia Time!", description=question["question"], color=discord.Color.blue())
        view = discord.ui.View(timeout=None)
        for ans in question["answers"]:
            view.add_item(self.AnswerButton(ans, self, ans))

        # Edit previous message if possible
        if "message" in session and session["message"]:
            try:
                await session["message"].edit(embed=embed, view=view)
            except Exception as e:
                print(f"[ERROR] Failed to edit previous message: {e}")
        else:
            # Send a new message in channel
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                msg = await channel.send(embed=embed, view=view)
                session["message"] = msg

    # ------------------- Slash Commands -------------------
    @app_commands.command(name="trivia", description="Start a trivia session")
    @app_commands.describe(category="Category ID (optional)")
    async def trivia(self, interaction: discord.Interaction, category: int = None):
        cid = str(interaction.channel_id)
        if cid in self.active_sessions:
            await interaction.response.send_message("A trivia session is already running in this channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)
        question = await self.fetch_question(category)
        if not question:
            await interaction.followup.send("❌ Failed to fetch a trivia question.", ephemeral=True)
            return

        msg = await interaction.followup.send(embed=discord.Embed(title="Trivia Time!", description=question["question"], color=discord.Color.blue()), view=discord.ui.View(timeout=None))
        self.active_sessions[cid] = {"question": question, "players": {}, "category": category, "message": msg}
        self.save_sessions()

        # Add buttons
        view = discord.ui.View(timeout=None)
        for ans in question["answers"]:
            view.add_item(self.AnswerButton(ans, self, ans))
        await msg.edit(view=view)

    @app_commands.command(name="trivia_stop", description="Stop an ongoing trivia session in this channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def trivia_stop(self, interaction: discord.Interaction):
        cid = str(interaction.channel_id)
        if cid not in self.active_sessions:
            await interaction.response.send_message("❌ No active trivia session in this channel.", ephemeral=True)
            return

        self.active_sessions.pop(cid)
        self.save_sessions()
        await interaction.response.send_message("✅ Trivia session stopped.", ephemeral=True)

    @app_commands.command(name="trivia_leaderboard", description="Show trivia leaderboard")
    @app_commands.describe(type="global or server", top="Top N users")
    async def trivia_leaderboard(self, interaction: discord.Interaction, type: str = "server", top: int = 10):
        lb = self.data["server_leaderboards"].get(str(interaction.guild_id), {}) if type == "server" else self.data["global_leaderboard"]
        sorted_lb = sorted(lb.items(), key=lambda x: x[1]["wins"], reverse=True)[:top]

        desc = ""
        for uid, stats in sorted_lb:
            member = interaction.guild.get_member(int(uid)) if interaction.guild else None
            name = member.display_name if member else f"User {uid}"
            desc += f"**{name}** - Wins: {stats['wins']}, Games: {stats['games_played']}\n"

        embed = discord.Embed(title=f"Trivia Leaderboard ({type})", description=desc or "No data yet.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Trivia(bot))
