import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import json
import random
import asyncio
import re

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel = None
        self.round = 0
        self.game_in_progress = False
        self.streaks = {}  # player_name -> streak
        self.round_scores = {}  # player_name -> score
        self.word = ""
        self.word_display = []
        self.hearts = 5
        self.timer = 60
        self.used_hints = []
        self.starter_hint = ""
        self.word_entry = {}
        self.previous_words = []
        self.word_list = self.load_words()
        self.timer_task = None

    # ===== Load words.json =====
    def load_words(self):
        path = os.path.join(os.path.dirname(__file__), "../data/words.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Flatten all categories into one list
            all_words = []
            for category in data.values():
                all_words.extend(category)
            return all_words
        except Exception as e:
            print("Error loading words.json:", e)
            return []

    # ===== Start Game =====
    @app_commands.command(name="gamestart", description="Start a new Guess the Word game")
    async def gamestart(self, interaction: discord.Interaction):
        if self.game_in_progress:
            await interaction.response.send_message(
                "A game is already in progress!", ephemeral=True
            )
            return

        self.game_in_progress = True
        self.channel = interaction.channel
        self.round += 1
        self.round_scores = {}
        self.used_hints = []
        self.hearts = 5
        self.timer = 60

        # Select a word not recently used
        available_words = [w for w in self.word_list if w["word"].upper() not in self.previous_words]
        if not available_words:
            # Reset previous_words if exhausted
            self.previous_words = []
            available_words = self.word_list.copy()

        self.word_entry = random.choice(available_words)
        self.previous_words.append(self.word_entry["word"].upper())
        self.word = self.word_entry["word"].upper()
        self.starter_hint = self.word_entry.get("start_hint") or self.word_entry.get("hint1", "No hint available")
        self.word_display = ["⬜"] * len(self.word)

        await interaction.response.send_message("Starting new game...", ephemeral=False)
        await self.send_round_embed()

        # Start timer countdown
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
        self.timer_task = self.bot.loop.create_task(self.timer_countdown())

    # ===== Hint Command =====
    @app_commands.command(name="hint", description="Get a hint for the current word")
    async def hint(self, interaction: discord.Interaction):
        player = interaction.user.name

        if not self.game_in_progress:
            await interaction.response.send_message(
                "No game is currently running. Use `/gamestart` to start!", ephemeral=True
            )
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

    # ===== Timer countdown =====
    async def timer_countdown(self):
        while self.timer > 0:
            await asyncio.sleep(1)
            self.timer -= 1
            if not self.game_in_progress:
                return
            if self.timer in [30, 15]:
                await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.timer} seconds remaining ⠀ּ ּ    ✧")
        if self.game_in_progress:
            await self.game_over()

    # ===== Process guesses =====
    async def process_guess(self, player: str, guess: str):
        if not self.game_in_progress:
            return

        guess_clean = re.sub(r"[^A-Za-z]", "", guess).upper()
        correct_clean = re.sub(r"[^A-Za-z]", "", self.word).upper()

        if guess_clean not in [re.sub(r"[^A-Za-z]", "", w["word"]).upper() for w in self.word_list]:
            return False  # ignore invalid words

        # Wordle coloring
        colored = []
        for i, c in enumerate(guess_clean):
            if i < len(correct_clean):
                if c == correct_clean[i]:
                    colored.append("🟩")
                elif c in correct_clean:
                    colored.append("🟨")
                else:
                    colored.append("⬜")
            else:
                colored.append("⬜")
        self.word_display = colored

        # Update round_scores even if not correct
        self.round_scores[player] = self.round_scores.get(player, 0)

        if guess_clean == correct_clean:
            self.round_scores[player] += 1
            self.streaks[player] = self.streaks.get(player, 0) + 1
            await self.channel.send(f"🎉 {player} guessed the word! 🔥 Streak: {self.streaks[player]}")
            await self.send_mini_leaderboard()
            await self.game_over()
        else:
            await self.send_round_embed()

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

    # ===== Game Over =====
    async def game_over(self):
        if not self.game_in_progress:
            return
        self.game_in_progress = False

        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        embed = discord.Embed(color=0x1b1c23)
        embed.add_field(
            name="˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ",
            value=f"The word was: {self.word}\nUse `/gamestart` to play again",
            inline=False,
        )
        await self.channel.send(embed=embed)
        self.word = ""
        self.round_scores = {}

# ===== Setup =====
async def setup(bot):
    await bot.add_cog(Game(bot))