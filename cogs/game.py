import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import random
import asyncio
import re

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel: discord.TextChannel | None = None
        self.game_in_progress = False
        self.starter_player = None
        self.round = 0
        self.streaks = {}         # player_name -> streak
        self.round_scores = {}    # player_name -> round points
        self.total_scores = {}    # player_name -> total points
        self.word = ""
        self.word_display = []
        self.hearts = 5
        self.timer = 60
        self.used_hints = []
        self.starter_hint = ""
        self.word_entry = {}
        self.word_list = self.load_words()
        self.timer_task: asyncio.Task | None = None
        self.previous_words = []  # words used recently

    # ===== Load words.json =====
    def load_words(self):
        path = os.path.join(os.path.dirname(__file__), "../data/words.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_words = []
                for cat in data.values():
                    all_words.extend(cat)
                return all_words
        except Exception as e:
            print("Error loading words.json:", e)
            return []

    # ===== Start Game Slash Command =====
    @app_commands.command(name="gamestart", description="Start a new Guess the Word game")
    async def gamestart(self, interaction: discord.Interaction):
        if self.game_in_progress:
            await interaction.response.send_message(
                "A game is already in progress!", ephemeral=True
            )
            return

        await interaction.response.defer()
        self.game_in_progress = True
        self.starter_player = interaction.user.name
        self.channel = interaction.channel
        self.round += 1
        self.round_scores = {}
        self.used_hints = []
        self.hearts = 5
        self.timer = 60

        # Select a word not recently used
        available_words = [w for w in self.word_list if w["word"].upper() not in self.previous_words]
        if not available_words:
            available_words = self.word_list
            self.previous_words = []

        self.word_entry = random.choice(available_words)
        self.word = self.word_entry["word"].upper()
        self.previous_words.append(self.word)
        self.starter_hint = self.word_entry.get("start_hint", "No hint available")
        self.word_display = ["⬜"] * len(self.word)

        await interaction.followup.send(f"🎮 Starting Round {self.round}!")
        await self.send_round_embed()

        # Start timer countdown
        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = self.bot.loop.create_task(self.timer_countdown())

    # ===== Stop Game Slash Command =====
    @app_commands.command(name="stopgame", description="Stop the current game")
    async def stopgame(self, interaction: discord.Interaction):
        if not self.game_in_progress:
            await interaction.response.send_message("No game is running.", ephemeral=True)
            return
        if interaction.user.name != self.starter_player:
            await interaction.response.send_message("Only the starter player can stop the game.", ephemeral=True)
            return

        await interaction.response.send_message("Game stopped by the starter player.")
        await self.end_game()

    # ===== Leaderboard Slash Command =====
    @app_commands.command(name="leaderboard", description="Show total points leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        if not self.total_scores:
            await interaction.response.send_message("No points yet!")
            return

        embed = discord.Embed(title="🏆 Leaderboard", color=0x1b1c23)
        sorted_scores = sorted(self.total_scores.items(), key=lambda x: x[1], reverse=True)
        for player, score in sorted_scores:
            embed.add_field(name=player, value=f"{score} Points", inline=False)
        await interaction.response.send_message(embed=embed)

    # ===== Hint Command =====
    @app_commands.command(name="hint", description="Get a hint for the current word")
    async def hint(self, interaction: discord.Interaction):
        if not self.game_in_progress:
            await interaction.response.send_message("No game is running.", ephemeral=True)
            return

        all_hints = [
            self.word_entry.get("hint1"),
            self.word_entry.get("hint2"),
            self.word_entry.get("hint3"),
        ]
        available_hints = [h for h in all_hints if h and h not in self.used_hints]

        if not available_hints:
            await interaction.response.send_message("No more hints available!", ephemeral=True)
            return

        hint_text = random.choice(available_hints)
        self.used_hints.append(hint_text)
        self.hearts = max(self.hearts - 1, 0)
        await self.send_round_embed()
        await interaction.response.send_message(f"Hint: {hint_text}", ephemeral=True)

    # ===== Timer Countdown =====
    async def timer_countdown(self):
        while self.timer > 0:
            await asyncio.sleep(1)
            self.timer -= 1
            if self.timer in [30, 15]:
                await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.timer} seconds remaining ⠀ּ ּ    ✧")
        await self.end_game(timeout=True)

    # ===== Process guesses automatically from messages =====
    async def process_guess(self, message: discord.Message):
        if not self.game_in_progress:
            return
        if message.channel != self.channel:
            return

        guess = re.sub(r"\s+", "", message.content).upper()
        word_clean = re.sub(r"\s+", "", self.word).upper()
        player = message.author.name

        # Ignore words not in words.json
        if guess not in [w["word"].upper().replace(" ", "") for w in self.word_list]:
            return

        # Wordle effect
        colored = []
        for i, c in enumerate(guess):
            if i < len(word_clean):
                if c == word_clean[i]:
                    colored.append("🟩")
                elif c in word_clean:
                    colored.append("🟨")
                else:
                    colored.append("⬛")
            else:
                colored.append("⬛")
        self.word_display = colored
        await self.send_round_embed()

        # Check if correct
        if guess == word_clean:
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.streaks[player] = self.streaks.get(player, 0) + 1
            self.total_scores[player] = self.total_scores.get(player, 0) + 1
            await self.channel.send(f"🎉 {player} guessed the word! 🔥 Streak: {self.streaks[player]}")
            await self.send_mini_leaderboard()
            await self.end_game()
        else:
            self.round_scores.setdefault(player, 0)

    # ===== Main round embed =====
    async def send_round_embed(self):
        embed = discord.Embed(color=0x1b1c23)
        embed.title = (
            f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟᰍᣟᣟᣟ⡟ᣟᣟᣟ꒰ Round {self.round} ꒱ᣟᣟᣟ꒱"
        )
        embed.add_field(
            name="﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚",
            value=f"﹒🍥﹒ᣟᣟ୧ᣟᣟ {self.timer}s ᣟᣟᣟ﹒♡﹒ᣟᣟ˚",
            inline=False,
        )

        streak_display = max(self.streaks.values(), default=0)
        embed.add_field(
            name="♩  ﹒ ﹒  Streak  ﹒ ୨୧",
            value=f"ᣟ♩ᣟᣟ﹒ᣟ﹒ᣟ 🔥 {streak_display} ᣟ﹒ᣟ୨୧",
            inline=False,
        )

        embed.add_field(name="Word:", value="".join(self.word_display), inline=False)
        hearts_display = "❤️" * self.hearts + "🖤" * (5 - self.hearts)
        embed.add_field(name="⃕⠀⠀Timer 𓂃　۪ ׄ", value=hearts_display, inline=False)
        embed.add_field(name="⃕⠀⠀starter hint 𓂃　۪ ׄ", value=self.starter_hint, inline=False)
        embed.add_field(name="⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ", value="\n".join(self.used_hints) or "None", inline=False)

        await self.channel.send(embed=embed)

    # ===== Mini leaderboard =====
    async def send_mini_leaderboard(self):
        lines = []
        sorted_scores = sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True)
        for player, score in sorted_scores:
            lines.append(f"◡◡  <:CC_trophy:1474577678790299821> {player} : {score} Points ♡  ࣪")
        embed = discord.Embed(color=0x1b1c23, description="\n".join(lines) or "No scores yet")
        await self.channel.send(embed=embed)

    # ===== End Game =====
    async def end_game(self, timeout=False):
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

        embed = discord.Embed(color=0x1b1c23)
        title = "Game Over ⏰" if timeout else "Game Finished ✅"
        embed.add_field(
            name=f"˚⠀⠀♡⃕⠀⠀{title} 𓂃　۪ ׄ",
            value=f"The word was: {self.word}\nUse `/gamestart` to play again",
            inline=False,
        )
        await self.channel.send(embed=embed)

        # Reset state for next game
        self.word = ""
        self.word_display = []
        self.hearts = 5
        self.timer = 60
        self.used_hints = []
        self.round_scores = {}
        self.starter_hint = ""
        self.game_in_progress = False
        self.starter_player = None

    # ===== Listen for messages to process guesses =====
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        await self.process_guess(message)

# ===== Setup =====
async def setup(bot):
    await bot.add_cog(Game(bot))