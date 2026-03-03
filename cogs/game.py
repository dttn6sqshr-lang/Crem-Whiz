import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
import asyncio
import re

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/words.json")

def normalize(text: str):
    return re.sub(r"[^A-Z]", "", text.upper())

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_in_progress = False
        self.channel = None
        self.starter_player = None

        self.word = ""
        self.word_entry = {}
        self.word_display = []
        self.used_words = []

        self.timer = 60
        self.hearts = 5
        self.round = 0
        self.timer_task = None

        self.used_hints = []
        self.streaks = {}
        self.round_scores = {}
        self.leaderboard = {}

        self.words = self.load_words()

    # -------- LOAD WORDS --------
    def load_words(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_words = []
        for cat in data.values():
            all_words.extend(cat)
        return all_words

    # -------- START GAME --------
    @app_commands.command(name="gamestart", description="Start a Guess the Word game")
    async def gamestart(self, interaction: discord.Interaction):
        if self.game_in_progress:
            await interaction.response.send_message("Game already in progress.", ephemeral=True)
            return

        self.game_in_progress = True
        self.channel = interaction.channel
        self.starter_player = interaction.user

        self.round += 1
        self.round_scores = {}
        self.used_hints = []
        self.hearts = 5
        self.timer = 60

        choices = [w for w in self.words if w["word"] not in self.used_words]
        self.word_entry = random.choice(choices)
        self.word = self.word_entry["word"].upper()
        self.used_words.append(self.word)

        if len(self.used_words) > 5:
            self.used_words.pop(0)

        self.word_display = ["⬜"] * len(self.word)

        await interaction.response.send_message("Starting game...")
        await self.send_round_embed()

        self.timer_task = asyncio.create_task(self.timer_countdown())

    # -------- STOP GAME --------
    @app_commands.command(name="stopgame", description="Stop the current game")
    async def stopgame(self, interaction: discord.Interaction):
        if not self.game_in_progress:
            await interaction.response.send_message("No game running.", ephemeral=True)
            return

        if interaction.user != self.starter_player:
            await interaction.response.send_message("Only the starter can stop the game.", ephemeral=True)
            return

        await interaction.response.send_message("Game stopped.")
        await self.end_game(force=True)

    # -------- LEADERBOARD --------
    @app_commands.command(name="leaderboard", description="Show global leaderboard")
    async def leaderboard_cmd(self, interaction: discord.Interaction):
        if not self.leaderboard:
            await interaction.response.send_message("No scores yet.")
            return

        lines = []
        sorted_scores = sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True)
        for user, score in sorted_scores:
            lines.append(f"◡◡ 🏆 {user} : {score} Points ♡")

        embed = discord.Embed(color=0x1b1c23, description="\n".join(lines))
        await interaction.response.send_message(embed=embed)

    # -------- TIMER --------
    async def timer_countdown(self):
        while self.timer > 0 and self.game_in_progress:
            await asyncio.sleep(1)
            self.timer -= 1
            if self.timer in (30, 15):
                await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.timer} seconds remaining ⠀ּ ּ    ✧")

        if self.game_in_progress:
            await self.end_game()

    # -------- CHAT LISTENER --------
    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.game_in_progress:
            return
        if message.channel != self.channel:
            return
        if message.author.bot:
            return

        guess = normalize(message.content)
        target = normalize(self.word)

        valid_words = [normalize(w["word"]) for w in self.words]
        if guess not in valid_words:
            return

        await self.process_guess(message.author.name, guess)

    # -------- PROCESS GUESS --------
    async def process_guess(self, player, guess):
        colored = []
        target = normalize(self.word)

        for i, c in enumerate(guess):
            if i < len(target):
                if c == target[i]:
                    colored.append("🟩")
                elif c in target:
                    colored.append("🟨")
                else:
                    colored.append("⬛")
            else:
                colored.append("⬛")

        self.word_display = colored

        await self.send_round_embed()

        if guess == target:
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.streaks[player] = self.streaks.get(player, 0) + 1
            self.leaderboard[player] = self.leaderboard.get(player, 0) + 1

            await self.send_mini_leaderboard()
            await self.end_game()

    # -------- EMBED --------
    async def send_round_embed(self):
        embed = discord.Embed(color=0x1b1c23)
        embed.title = f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   Round {self.round}"

        embed.add_field(
            name="﹒🍥﹒ Time Left ﹒♡﹒",
            value=f"{self.timer}s",
            inline=False,
        )

        streak_display = max(self.streaks.values(), default=0)
        embed.add_field(
            name="Streak",
            value=f"🔥 {streak_display}",
            inline=False,
        )

        embed.add_field(name="Word", value="".join(self.word_display), inline=False)

        hearts_display = "❤️" * self.hearts + "🖤" * (5 - self.hearts)
        embed.add_field(name="⃕⠀⠀Timer 𓂃", value=hearts_display, inline=False)

        embed.add_field(
            name="⃕⠀⠀starter hint 𓂃",
            value=self.word_entry.get("start_hint", "No hint"),
            inline=False,
        )

        embed.add_field(
            name="⠀♡⃕⠀⠀used hints 𓂃",
            value="\n".join(self.used_hints) or "None",
            inline=False,
        )

        await self.channel.send(embed=embed)

    # -------- MINI LEADERBOARD --------
    async def send_mini_leaderboard(self):
        lines = []
        sorted_scores = sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True)
        for player, score in sorted_scores:
            lines.append(f"◡◡ 🏆 {player} : {score} Points ♡")

        embed = discord.Embed(color=0x1b1c23, description="\n".join(lines))
        await self.channel.send(embed=embed)

    # -------- END GAME --------
    async def end_game(self, force=False):
        if self.timer_task:
            self.timer_task.cancel()

        embed = discord.Embed(color=0x1b1c23)
        embed.add_field(
            name="˚⠀⠀♡⃕⠀⠀game over 𓂃",
            value=f"The word was: **{self.word}**\nUse `/gamestart` to play again",
            inline=False,
        )
        await self.channel.send(embed=embed)

        self.game_in_progress = False
        self.word = ""
        self.word_display = []
        self.timer = 60
        self.hearts = 5
        self.used_hints = []
        self.round_scores = {}
        self.starter_player = None

async def setup(bot):
    await bot.add_cog(Game(bot))