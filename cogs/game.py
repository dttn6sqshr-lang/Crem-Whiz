import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from collections import defaultdict

# Load words once at startup
with open("data/words.json", "r") as f:
    WORDS = json.load(f)["All"]

class Game(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.current_word = None
        self.previous_word = None
        self.hints_used = 0
        self.mini_scoreboard = defaultdict(int)
        self.leaderboard = defaultdict(int)

    def start_new_round(self):
        """Pick a random word avoiding previous word."""
        if not WORDS:
            return "No words available!"
        new_word = random.choice(WORDS)
        while new_word == self.previous_word and len(WORDS) > 1:
            new_word = random.choice(WORDS)
        self.current_word = new_word
        self.previous_word = new_word
        self.hints_used = 0
        return self.current_word["start_hint"]

    def next_hint(self):
        """Return the next hint."""
        self.hints_used += 1
        if self.hints_used == 1:
            return self.current_word.get("hint1", "No more hints!")
        elif self.hints_used == 2:
            return self.current_word.get("hint2", "No more hints!")
        elif self.hints_used == 3:
            return self.current_word.get("hint3", "No more hints!")
        else:
            return "No more hints!"

    def check_answer(self, guess):
        return self.current_word and self.current_word["word"].lower() == guess.lower()

    def get_points(self):
        difficulty = self.current_word.get("difficulty", 1)
        return max(1, difficulty - self.hints_used)

    # ----------------- Slash Commands -----------------
    @app_commands.command(name="startgame", description="Start a new game round")
    async def startgame(self, interaction: discord.Interaction):
        self.mini_scoreboard.clear()
        hint = self.start_new_round()
        await interaction.response.send_message(f"🎮 New round! First hint:\n**{hint}**")

    @app_commands.command(name="hint", description="Get the next hint for the current word")
    async def hint(self, interaction: discord.Interaction):
        if not self.current_word:
            await interaction.response.send_message("No active round. Use /startgame first!")
            return
        hint_text = self.next_hint()
        await interaction.response.send_message(f"💡 Hint: {hint_text}")

    @app_commands.command(name="answer", description="Submit your guess for the current word")
    @app_commands.describe(guess="Your guess for the current word")
    async def answer(self, interaction: discord.Interaction, guess: str):
        user = interaction.user.name
        if not self.current_word:
            await interaction.response.send_message("No active round. Use /startgame first!")
            return
        if self.check_answer(guess):
            points = self.get_points()
            self.mini_scoreboard[user] += points
            self.leaderboard[user] += points
            correct_word = self.current_word["word"]
            new_hint = self.start_new_round()
            await interaction.response.send_message(
                f"✅ Correct, {user}! You earned {points} point(s).\n"
                f"📊 Mini Score: {self.mini_scoreboard[user]}\n"
                f"🏆 Total Leaderboard: {self.leaderboard[user]}\n"
                f"Next round! First hint:\n**{new_hint}**"
            )
        else:
            await interaction.response.send_message(f"❌ Incorrect, {user}! Try again.")

    @app_commands.command(name="miniscore", description="Check your mini score")
    async def miniscore(self, interaction: discord.Interaction):
        user = interaction.user.name
        score = self.mini_scoreboard.get(user, 0)
        await interaction.response.send_message(f"📊 {user} - Mini Score: {score}")

    @app_commands.command(name="leaderboard", description="View the total leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        if not self.leaderboard:
            await interaction.response.send_message("Leaderboard is empty.")
            return
        sorted_lb = sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True)
        leaderboard_text = "\n".join([f"{user}: {score}" for user, score in sorted_lb])
        await interaction.response.send_message(f"🏆 Leaderboard:\n{leaderboard_text}")