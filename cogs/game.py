import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import asyncio
from collections import defaultdict

# Load words
with open("data/words.json", "r") as f:
    WORDS_LIST = json.load(f)["All"]
    WORDS = [w["word"].upper() for w in WORDS_LIST]
    WORD_DETAILS = {w["word"].upper(): w for w in WORDS_LIST}

ROUND_TIME = 60  # seconds per round

class Game(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.current_word = None
        self.hints_used = 0
        self.round_task = None
        self.guesses_per_player = defaultdict(int)
        self.mini_scoreboard = defaultdict(int)
        self.leaderboard = defaultdict(int)
        self.active_game = False

    # ---------------- Helper functions ----------------
    def pick_word(self):
        word = random.choice(WORDS)
        self.current_word = WORD_DETAILS[word]
        self.hints_used = 0
        self.guesses_per_player.clear()
        return self.current_word["start_hint"]

    def next_hint(self):
        self.hints_used += 1
        if self.hints_used == 1:
            return self.current_word.get("hint1", "No more hints!")
        elif self.hints_used == 2:
            return self.current_word.get("hint2", "No more hints!")
        elif self.hints_used == 3:
            return self.current_word.get("hint3", "No more hints!")
        else:
            return "No more hints!"

    def calculate_points(self):
        return max(1, self.current_word.get("difficulty", 1) - self.hints_used)

    def wordle_feedback(self, guess):
        guess = guess.upper()
        word = self.current_word["word"].upper()
        word_letters = list(word)
        guess_letters = list(guess)
        result = [""] * len(guess_letters)

        # First pass: correct letter + correct position
        for i, l in enumerate(guess_letters):
            if i < len(word_letters) and l == word_letters[i]:
                result[i] = "✅"
                word_letters[i] = None

        # Second pass: correct letter wrong position
        for i, l in enumerate(guess_letters):
            if result[i] == "":
                if l in word_letters:
                    result[i] = "🟡"
                    word_letters[word_letters.index(l)] = None
                else:
                    result[i] = "❌"

        return "".join(result)

    # ---------------- Timer ----------------
    async def round_timer(self, channel):
        total_time = ROUND_TIME
        warnings = [30, 15]
        try:
            for remaining in range(total_time, 0, -1):
                if remaining in warnings:
                    hints_left = max(0, 3 - self.hints_used)
                    guesses_left_per_player = {
                        user: max(0, 3 - guesses)
                        for user, guesses in self.guesses_per_player.items()
                    }
                    guesses_text = ", ".join([f"{user}: {g}" for user, g in guesses_left_per_player.items()])
                    if not guesses_text:
                        guesses_text = "No guesses made yet"
                    await channel.send(
                        f"⏳ {remaining} seconds remaining!\n"
                        f"💡 Hints left: {hints_left}\n"
                        f"✏️ Guesses left per player: {guesses_text}"
                    )
                await asyncio.sleep(1)

            self.active_game = False
            await channel.send(
                f"⏰ Time's up! The word was **{self.current_word['word']}**.\n"
                "Game over! Use /startgame to play again."
            )
        except asyncio.CancelledError:
            return

    # ---------------- Slash Commands ----------------
    @app_commands.command(name="startgame", description="Start a new game")
    async def startgame(self, interaction: discord.Interaction):
        if self.active_game:
            await interaction.response.send_message("A game is already in progress!")
            return
        self.active_game = True
        self.mini_scoreboard.clear()
        hint = self.pick_word()
        word_length_display = " ".join(["_" for _ in self.current_word["word"]])
        await interaction.response.send_message(
            f"🎮 New game started!\nWord length: {word_length_display}\nFirst hint: **{hint}**"
        )
        self.round_task = asyncio.create_task(self.round_timer(interaction.channel))

    @app_commands.command(name="hint", description="Get a hint for the current word")
    async def hint(self, interaction: discord.Interaction):
        if not self.active_game or not self.current_word:
            await interaction.response.send_message("No active game! Use /startgame first.")
            return
        if self.hints_used >= 3:
            await interaction.response.send_message("No more hints left for this round!")
            return
        hint_text = self.next_hint()
        await interaction.response.send_message(f"💡 Hint: {hint_text}")

    @app_commands.command(name="miniscore", description="View mini scoreboard")
    async def miniscore(self, interaction: discord.Interaction):
        if not self.mini_scoreboard:
            await interaction.response.send_message("No scores yet.")
            return
        sorted_scores = sorted(self.mini_scoreboard.items(), key=lambda x: x[1], reverse=True)
        msg = "\n".join([f"{user} - {score}" for user, score in sorted_scores])
        await interaction.response.send_message(f"📊 Mini Scoreboard:\n{msg}")

    @app_commands.command(name="leaderboard", description="View total leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        if not self.leaderboard:
            await interaction.response.send_message("No scores yet.")
            return
        sorted_scores = sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True)
        msg = "\n".join([f"{user} - {score}" for user, score in sorted_scores])
        await interaction.response.send_message(f"🏆 Leaderboard:\n{msg}")

    # ---------------- Message Listener ----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not self.active_game or not self.current_word:
            return

        user = message.author.name
        guess = message.content.strip().upper()

        # Only accept messages that match the word length
        if len(guess) != len(self.current_word["word"]):
            return

        # Check correct guess
        if guess == self.current_word["word"].upper():
            points = self.calculate_points()
            self.mini_scoreboard[user] += points
            self.leaderboard[user] += points

            await message.channel.send(
                f"✅ {user} guessed correctly! You earned {points} points.\n"
                f"📊 Mini Scoreboard:\n" +
                "\n".join([f"{u} - {s}" for u, s in self.mini_scoreboard.items()])
            )

            if self.round_task:
                self.round_task.cancel()
            # Start new round
            hint = self.pick_word()
            word_length_display = " ".join(["_" for _ in self.current_word["word"]])
            await message.channel.send(
                f"🎮 Next round!\nWord length: {word_length_display}\nFirst hint: **{hint}**"
            )
            self.round_task = asyncio.create_task(self.round_timer(message.channel))
        else:
            # Only reduce guesses if wrong
            self.guesses_per_player[user] += 1
            if self.guesses_per_player[user] > 3:
                await message.channel.send(f"{user}, you've already used all 3 guesses for this round!")
                return
            feedback = self.wordle_feedback(guess)
            await message.channel.send(f"{user}: {feedback}")