import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
import asyncio

EMBED_COLOR = 0x1b1c23

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel = None
        self.round = 0
        self.word = ""
        self.word_entry = {}
        self.word_display = []
        self.word_list = self.load_words()
        self.timer = 60
        self.timer_task = None
        self.hearts = 5
        self.used_hints = []
        self.starter_hint = ""
        self.round_scores = {}
        self.streaks = {}
        self.game_active = False

    # ===== NORMALIZE WORDS (bee keeping == beekeeping) =====
    def normalize(self, text: str):
        return "".join(c for c in text.upper() if c.isalnum())

    # ===== LOAD WORDS =====
    def load_words(self):
        path = os.path.join(os.path.dirname(__file__), "../data/words.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "All" in data:
                    return data["All"]
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            print("Error loading words.json:", e)
            return []

    # ===== START NEW ROUND =====
    async def start_new_round(self):
        self.round += 1
        self.round_scores = {}
        self.used_hints = []
        self.timer = 60
        self.hearts = 5
        self.game_active = True

        self.word_entry = random.choice(self.word_list)
        self.word = self.word_entry["word"].upper()
        self.word_display = ["⬜"] * len(self.normalize(self.word))
        self.starter_hint = self.word_entry.get("start_hint", "No hint")

        await self.send_round_embed()

        if self.timer_task:
            self.timer_task.cancel()

        self.timer_task = asyncio.create_task(self.timer_countdown())

    # ===== SLASH COMMAND =====
    @app_commands.command(name="gamestart", description="Start Guess the Word")
    async def gamestart(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not self.word_list:
            await interaction.followup.send("No words loaded.")
            return

        self.channel = interaction.channel
        self.round = 0
        self.streaks = {}

        if self.timer_task:
            self.timer_task.cancel()

        await self.start_new_round()

    # ===== HINT =====
    @app_commands.command(name="hint", description="Get a hint")
    async def hint(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not self.game_active:
            await interaction.followup.send("No game running.")
            return

        hints = [
            self.word_entry.get("hint1"),
            self.word_entry.get("hint2"),
            self.word_entry.get("hint3"),
        ]

        available = [h for h in hints if h and h not in self.used_hints]

        if not available:
            await interaction.followup.send("No more hints.")
            return

        hint_text = random.choice(available)
        self.used_hints.append(hint_text)
        self.hearts = max(self.hearts - 1, 0)

        await self.send_round_embed()
        await interaction.followup.send(hint_text)

    # ===== TIMER =====
    async def timer_countdown(self):
        try:
            while self.timer > 0 and self.game_active:
                await asyncio.sleep(1)
                self.timer -= 1

                if self.timer in (30, 15):
                    await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.timer} seconds remaining ⠀ּ ּ    ✧")

            if self.game_active:
                await self.game_over()
        except asyncio.CancelledError:
            pass

    # ===== LISTEN FOR GUESSES =====
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.game_active:
            return
        if message.author.bot:
            return
        if message.channel != self.channel:
            return

        guess = message.content.strip()

        if len(self.normalize(guess)) != len(self.normalize(self.word)):
            return

        await self.process_guess(message.author.display_name, guess)

    # ===== PROCESS GUESS =====
    async def process_guess(self, player, guess):
        clean_guess = self.normalize(guess)
        clean_word = self.normalize(self.word)

        colored = []
        for i, c in enumerate(clean_guess):
            if i < len(clean_word) and c == clean_word[i]:
                colored.append("🟩")
            elif c in clean_word:
                colored.append("🟨")
            else:
                colored.append("⬛")

        self.word_display = colored

        if clean_guess == clean_word:
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.streaks[player] = self.streaks.get(player, 0) + 1

            await self.channel.send(f"🎉 {player} guessed the word! 🔥 {self.streaks[player]} streak")
            await self.send_mini_leaderboard()

            self.game_active = False
            if self.timer_task:
                self.timer_task.cancel()

            await asyncio.sleep(2)
            await self.start_new_round()
        else:
            self.round_scores.setdefault(player, 0)
            await self.send_round_embed()

    # ===== ROUND EMBED =====
    async def send_round_embed(self):
        embed = discord.Embed(color=EMBED_COLOR)

        embed.title = (
            f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟᰍᣟᣟᣟ⟡ᣟᣟᣟ꒰ Round {self.round} ꒱ᣟᣟᣟ꒱"
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

        embed.add_field(name="▪️▪️▪️▪️▪️", value="".join(self.word_display), inline=False)

        hearts_display = "❤️" * self.hearts + "🖤" * (5 - self.hearts)
        embed.add_field(name="⃕⠀⠀Timer 𓂃　۪ ׄ", value=hearts_display, inline=False)
        embed.add_field(name="⃕⠀⠀starter hint 𓂃　۪ ׄ", value=self.starter_hint, inline=False)
        embed.add_field(
            name="⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ",
            value="\n".join(self.used_hints) or "None",
            inline=False,
        )

        await self.channel.send(embed=embed)

    # ===== MINI LEADERBOARD =====
    async def send_mini_leaderboard(self):
        lines = []
        sorted_scores = sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True)
        for player, score in sorted_scores:
            lines.append(f"◡◡  <:CC_trophy:1474577678790299821> {player} : {score} Points ♡  ࣪")

        embed = discord.Embed(color=EMBED_COLOR, description="\n".join(lines))
        await self.channel.send(embed=embed)

    # ===== GAME OVER =====
    async def game_over(self):
        self.game_active = False

        embed = discord.Embed(color=EMBED_COLOR)
        embed.add_field(
            name="˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ",
            value=f"The word was: **{self.word}**\nUse `/gamestart` to play again",
            inline=False,
        )
        await self.channel.send(embed=embed)

        if self.timer_task:
            self.timer_task.cancel()

        self.word = ""

async def setup(bot):
    await bot.add_cog(Game(bot))