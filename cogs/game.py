import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
import asyncio

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel = None
        self.round = 0
        self.streaks = {}
        self.round_scores = {}
        self.word = ""
        self.word_display = []
        self.hearts = 5
        self.timer = 60
        self.used_hints = []
        self.starter_hint = ""
        self.word_entry = {}
        self.word_list = self.load_words()
        self.timer_task = None

    def load_words(self):
        path = os.path.join(os.path.dirname(__file__), "../data/words.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ================= SLASH COMMAND =================

    @app_commands.command(name="gamestart", description="Start a new Guess the Word game")
    async def gamestart(self, interaction: discord.Interaction):
        self.channel = interaction.channel
        self.round += 1
        self.round_scores = {}
        self.used_hints = []
        self.hearts = 5
        self.timer = 60

        self.word_entry = random.choice(self.word_list)
        self.word = self.word_entry["word"].upper()
        self.starter_hint = self.word_entry.get("hint1", "No hint")
        self.word_display = ["⬜"] * len(self.word)

        await interaction.response.send_message("Game started!", ephemeral=True)
        await self.send_round_embed()

        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.timer_countdown())

    # ================= TIMER =================

    async def timer_countdown(self):
        while self.timer > 0:
            await asyncio.sleep(1)
            self.timer -= 1
            if self.timer in [30, 15]:
                await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.timer} seconds remaining ⠀ּ ּ    ✧")
        await self.game_over()

    # ================= CHAT GUESS =================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not self.word:
            return
        if message.channel != self.channel:
            return

        guess = message.content.strip().upper()
        words = [w["word"].upper() for w in self.word_list]
        if guess not in words:
            return

        await self.process_guess(message.author.name, guess)

    async def process_guess(self, player, guess):
        colored = []
        for i, c in enumerate(guess):
            if c == self.word[i]:
                colored.append("🟩")
            elif c in self.word:
                colored.append("🟨")
            else:
                colored.append("⬛")

        self.word_display = colored

        if guess == self.word:
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.streaks[player] = self.streaks.get(player, 0) + 1
            await self.send_mini_leaderboard()
            await self.game_over()
        else:
            await self.send_round_embed()

    # ================= EMBEDS =================

    async def send_round_embed(self):
        embed = discord.Embed(color=0x1b1c23)

        embed.title = f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟᰍᣟᣟᣟ⡟ᣟᣟᣟ꒰ Round {self.round} ꒱ᣟᣟᣟ꒱"

        embed.add_field(
            name="﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚",
            value=f"﹒🍥﹒ᣟᣟ୧ᣟᣟ {self.timer}s ᣟᣟᣟ﹒♡﹒ᣟᣟ˚",
            inline=False,
        )

        top_streak = max(self.streaks.values(), default=0)
        embed.add_field(
            name="♩  ﹒ ﹒  Streak  ﹒ ୨୧",
            value=f"ᣟ♩ᣟᣟ﹒ᣟ﹒ᣟ 🔥 {top_streak} ᣟ﹒ᣟ୨୧",
            inline=False,
        )

        embed.add_field(name="Word", value="".join(self.word_display), inline=False)

        hearts_display = "❤️" * self.hearts + "🖤" * (5 - self.hearts)
        embed.add_field(name="⃕⠀⠀Timer 𓂃　۪ ׄ", value=hearts_display, inline=False)

        embed.add_field(name="⃕⠀⠀starter hint 𓂃　۪ ׄ", value=self.starter_hint, inline=False)
        embed.add_field(name="⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ", value="\n".join(self.used_hints) or "None", inline=False)

        await self.channel.send(embed=embed)

    async def send_mini_leaderboard(self):
        lines = []
        for player, score in sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"◡◡  <:CC_trophy:1474577678790299821> {player} : {score} Points ♡  ࣪")

        embed = discord.Embed(color=0x1b1c23, description="\n".join(lines))
        await self.channel.send(embed=embed)

    async def game_over(self):
        embed = discord.Embed(color=0x1b1c23)
        embed.add_field(
            name="˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ",
            value=f"the word was: {self.word}\nuse /gamestart to play again",
            inline=False,
        )
        await self.channel.send(embed=embed)
        self.word = ""

async def setup(bot):
    await bot.add_cog(Game(bot))