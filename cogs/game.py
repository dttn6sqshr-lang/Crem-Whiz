import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import asyncio
from collections import defaultdict
import re

# Load words
with open("data/words.json", "r") as f:
    WORDS_LIST = json.load(f)["All"]
    WORDS = [w["word"].upper() for w in WORDS_LIST]
    WORD_DETAILS = {w["word"].upper(): w for w in WORDS_LIST}

ROUND_TIME = 60  # seconds per round
HEART_TOTAL = 5  # Total hearts per round

class Game(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.current_word = None
        self.hints_used = 0
        self.round_task = None
        self.mini_scoreboard = defaultdict(int)
        self.leaderboard = defaultdict(int)
        self.guess_streaks = defaultdict(int)
        self.extra_hints = defaultdict(int)
        self.active_game = False
        self.embed_message = None
        self.time_remaining = ROUND_TIME
        self.guessed_letters = []

    # ---------------- Helper functions ----------------
    def pick_word(self):
        word = random.choice(WORDS)
        self.current_word = WORD_DETAILS[word]
        self.hints_used = 0
        self.guessed_letters = []  # reset per round
        return self.current_word["start_hint"]

    def next_hint(self, user=None):
        self.hints_used += 1
        total_hints = 3 + (self.extra_hints.get(user, 0) if user else 0)
        if self.hints_used == 1:
            return self.current_word.get("hint1", "No more hints!"), total_hints - self.hints_used
        elif self.hints_used == 2:
            return self.current_word.get("hint2", "No more hints!"), total_hints - self.hints_used
        elif self.hints_used == 3:
            return self.current_word.get("hint3", "No more hints!"), total_hints - self.hints_used
        else:
            return "No more hints!", 0

    def calculate_points(self):
        return max(1, self.current_word.get("difficulty", 1) - self.hints_used)

    # ---------------- Wordle feedback ----------------
    def wordle_feedback(self, guess):
        guess = guess.upper()
        word = self.current_word["word"].upper()
        word_letters = list(word)
        guess_letters = list(guess)
        result = [""] * len(guess_letters)

        # First pass: correct letter + correct position
        for i, l in enumerate(guess_letters):
            if i < len(word_letters) and l == word_letters[i]:
                result[i] = "🟩"
                word_letters[i] = None

        # Second pass: correct letter wrong position
        for i, l in enumerate(guess_letters):
            if result[i] == "":
                if l in word_letters:
                    result[i] = "🟨"
                    word_letters[word_letters.index(l)] = None
                else:
                    result[i] = "⬛"

        # Track each letter status
        for l, r in zip(guess_letters, result):
            existing = next((x for x in self.guessed_letters if x[0] == l), None)
            if existing:
                if existing[1] == "🟩":
                    continue
                if existing[1] == "🟨" and r == "⬛":
                    continue
            self.guessed_letters.append((l, r))

        return "".join(result)

    def hearts_display(self):
        hearts_left = max(0, HEART_TOTAL - self.hints_used)
        return "❤️" * hearts_left + "🖤" * (HEART_TOTAL - hearts_left)

    def clean_message(self, msg):
        return re.sub(r'[^\w\s]', '', msg).strip().upper()

    def guessed_letters_display(self):
        if not self.guessed_letters:
            return "None yet."
        display = []
        for l, s in sorted(self.guessed_letters):
            display.append(f"{l}:{s}")
        return " ".join(display)

    def mini_leaderboard_embed(self):
        sorted_scores = sorted(self.mini_scoreboard.items(), key=lambda x: x[1], reverse=True)
        top_score = sorted_scores[0][1] if sorted_scores else 0
        lines = []
        for user, score in sorted_scores:
            trophy = " <:CC_trophy:1474577678790299821>" if score == top_score and score > 0 else ""
            lines.append(f"{user} - {score}{trophy}")
        return "\n".join(lines) if lines else "No scores yet."

    # ---------------- Timer ----------------
    async def round_timer(self):
        self.time_remaining = ROUND_TIME
        warnings = [30, 15]
        channel = self.embed_message.channel if self.embed_message else None
        try:
            while self.time_remaining > 0:
                await asyncio.sleep(1)
                self.time_remaining -= 1
                if self.time_remaining in warnings and channel:
                    await self.update_embed(channel, warning=f"{self.time_remaining}s remaining!")
            self.active_game = False
            if channel:
                await channel.send(f"⏰ Time's up! The word was **{self.current_word['word']}**.\nGame over! Use /startgame to play again.")
        except asyncio.CancelledError:
            return

    # ---------------- Embed Update ----------------
    async def update_embed(self, channel, warning=None, hint_text=None):
        word_length_display = "▪️" * len(self.current_word["word"])
        
        # Hints display
        hints_used_list = []
        if self.hints_used >= 1:
            hints_used_list.append(f"1️⃣ {self.current_word.get('hint1', 'No hint')}")
        if self.hints_used >= 2:
            hints_used_list.append(f"2️⃣ {self.current_word.get('hint2', 'No hint')}")
        if self.hints_used >= 3:
            hints_used_list.append(f"3️⃣ {self.current_word.get('hint3', 'No hint')}")
        hint_display = self.current_word["start_hint"]
        if hints_used_list:
            hint_display += "\n" + "\n".join(hints_used_list)
        if hint_text:
            hint_display += f"\n{hint_text}"

        embed = discord.Embed(
            title=f"🎮 Guess the Word! – Round",
            description=f"Word: {word_length_display}\nProgress: {self.hearts_display()}",
            color=discord.Color.green()
        )
        embed.add_field(name="Hints", value=hint_display, inline=False)
        embed.add_field(name="Mini Leaderboard", value=self.mini_leaderboard_embed(), inline=False)
        embed.add_field(name="Guessed Letters", value=self.guessed_letters_display(), inline=False)
        if warning:
            embed.set_footer(text=warning)

        # Delete old embed
        if self.embed_message:
            try:
                await self.embed_message.delete()
            except:
                pass
        # Send new embed
        self.embed_message = await channel.send(embed=embed)

    # ---------------- Slash Commands ----------------
    @app_commands.command(name="startgame", description="Start a new game")
    async def startgame(self, interaction: discord.Interaction):
        if self.active_game:
            await interaction.response.send_message("A game is already in progress!")
            return
        self.active_game = True
        self.mini_scoreboard.clear()
        hint = self.pick_word()
        await interaction.response.send_message(f"🎮 New game started! Word length: {'▪️'*len(self.current_word['word'])}\nFirst hint: **{hint}**")
        self.embed_message = await interaction.channel.send("Setting up game embed...")
        await self.update_embed(interaction.channel)
        self.round_task = asyncio.create_task(self.round_timer())

    @app_commands.command(name="hint", description="Get a hint for the current word")
    async def hint(self, interaction: discord.Interaction):
        if not self.active_game or not self.current_word:
            await interaction.response.send_message("No active game!")
            return
        user = interaction.user.name
        hint_text, hints_left = self.next_hint(user)
        await self.update_embed(interaction.channel)
        await interaction.response.send_message(f"💡 Hint: {hint_text}\nHints left: {hints_left}")

    @app_commands.command(name="miniscore", description="View mini scoreboard")
    async def miniscore(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏆 Mini Scoreboard",
            description=self.mini_leaderboard_embed(),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View total leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        sorted_scores = sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True)
        top_score = sorted_scores[0][1] if sorted_scores else 0
        lines = []
        for user, score in sorted_scores:
            trophy = " <:CC_trophy:1474577678790299821>" if score == top_score and score > 0 else ""
            lines.append(f"{user} - {score}{trophy}")
        msg = "\n".join(lines) if lines else "No scores yet."
        embed = discord.Embed(title="🏆 Leaderboard", description=msg, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    # ---------------- Message Listener ----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not self.active_game or not self.current_word:
            return
        user = message.author.name
        guess = self.clean_message(message.content)

        valid_words = {w.upper() for w in WORDS}
        if guess not in valid_words:
            return  # Ignore normal chat

        word_to_guess = self.current_word["word"].upper()
        if guess == word_to_guess:
            points = self.calculate_points()
            self.mini_scoreboard[user] += points
            self.leaderboard[user] += points

            # Streak handling
            self.guess_streaks[user] += 1
            if self.guess_streaks[user] > 0 and self.guess_streaks[user] % 3 == 0:
                self.extra_hints[user] += 1
                await message.channel.send(f"🔥 {user} has a {self.guess_streaks[user]}-round streak! +1 extra hint next round.")

            if self.round_task:
                self.round_task.cancel()

            hint = self.pick_word()
            self.embed_message = None
            await message.channel.send(f"🎉 {user} guessed correctly! Next round starting...")
            await self.update_embed(message.channel)
            self.round_task = asyncio.create_task(self.round_timer())
        else:
            feedback = self.wordle_feedback(guess)
            await self.update_embed(message.channel)
            await message.channel.send(f"{user}: {feedback}")