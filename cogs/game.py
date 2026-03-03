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
        self.word_list = self.load_words()

        self.word_entry = None
        self.word = ""
        self.word_display = []
        self.streaks = {}
        self.round_scores = {}

        self.timer = 60
        self.hearts = 5
        self.used_hints = []
        self.starter_hint = ""
        self.timer_task = None

    # ===== Load words.json =====
    def load_words(self):
        path = os.path.join(os.path.dirname(__file__), "../data/words.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

                if isinstance(data, dict) and "All" in data:
                    return data["All"]

                if isinstance(data, list):
                    return data

                print("Unexpected words.json format")
                return []

        except Exception as e:
            print("Error loading words.json:", e)
            return []

    # ===== Slash: /gamestart =====
    @app_commands.command(name="gamestart", description="Start a new Guess the Word game")
    async def gamestart(self, interaction: discord.Interaction):
        if not self.word_list:
            await interaction.response.send_message("No words loaded.", ephemeral=True)
            return

        self.channel = interaction.channel
        self.round += 1
        self.round_scores = {}
        self.used_hints = []
        self.timer = 60
        self.hearts = 5

        self.word_entry = random.choice(self.word_list)
        self.word = self.word_entry["word"].upper()
        self.word_display = ["⬜"] * len(self.word)

        self.starter_hint = self.word_entry.get("start_hint", "No hint")

        await interaction.response.send_message(" ")
        await self.send_round_embed()

        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.timer_countdown())

    # ===== Slash: /hint =====
    @app_commands.command(name="hint", description="Get a hint")
    async def hint(self, interaction: discord.Interaction):
        if not self.word:
            await interaction.response.send_message("No game running.", ephemeral=True)
            return

        all_hints = [
            self.word_entry.get("hint1"),
            self.word_entry.get("hint2"),
            self.word_entry.get("hint3"),
        ]

        available = [h for h in all_hints if h and h not in self.used_hints]

        if not available:
            await interaction.response.send_message("No more hints.", ephemeral=True)
            return

        hint = random.choice(available)
        self.used_hints.append(hint)
        self.hearts = max(self.hearts - 1, 0)

        await self.send_round_embed()
        await interaction.response.send_message(f"Hint: {hint}", ephemeral=True)

    # ===== Timer =====
    async def timer_countdown(self):
        while self.timer > 0:
            await asyncio.sleep(1)
            self.timer -= 1

            if self.timer in (30, 15):
                await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.timer} seconds remaining ⠀ּ ּ    ✧")

        await self.game_over()

    # ===== Guess processing =====
    async def process_guess(self, player: str, guess: str):
        guess = guess.upper()

        colored = []
        for i, c in enumerate(guess):
            if i < len(self.word):
                if c == self.word[i]:
                    colored.append("🟩")
                elif c in self.word:
                    colored.append("🟨")
                else:
                    colored.append("⬛")
            else:
                colored.append("⬛")

        self.word_display = colored

        if guess == self.word:
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.streaks[player] = self.streaks.get(player, 0) + 1

            await self.channel.send(f"🎉 {player} guessed the word!")
            await self.send_mini_leaderboard()
            await self.game_over()
        else:
            await self.send_round_embed()

    # ===== Main Embed =====
    async def send_round_embed(self):
        embed = discord.Embed(color=EMBED_COLOR)

        embed.description = (
            f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟᰍᣟᣟᣟ⟡ᣟᣟᣟ꒰ Round {self.round} ꒱ᣟᣟᣟ꒱\n"
            f"﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚   |   ﹒🍥﹒ᣟᣟ୧ᣟᣟ {self.timer}s ᣟᣟᣟ﹒♡﹒ᣟᣟ˚\n"
            f"♩  ﹒ ﹒  Streak  ﹒ ୨୧   |   ᣟ♩ᣟᣟ﹒ᣟ﹒ᣟ 🔥 {max(self.streaks.values(), default=0)} ᣟ﹒ᣟ୨୧\n\n"
            f"{''.join(self.word_display)}\n\n"
            f"⃕⠀⠀Timer 𓂃　۪ ׄ\n"
            f"{'❤️'*self.hearts + '🖤'*(5-self.hearts)}\n\n"
            f"⃕⠀⠀starter hint 𓂃　۪ ׄ\n{self.starter_hint}\n\n"
            f"⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ\n{chr(10).join(self.used_hints) if self.used_hints else 'None'}"
        )

        await self.channel.send(embed=embed)

    # ===== Mini leaderboard =====
    async def send_mini_leaderboard(self):
        lines = []
        sorted_scores = sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True)

        for player, score in sorted_scores:
            lines.append(f"◡◡  <:CC_trophy:1474577678790299821> {player} : {score} Points ♡  ࣪")

        embed = discord.Embed(color=EMBED_COLOR, description="\n".join(lines))
        await self.channel.send(embed=embed)

    # ===== Game Over =====
    async def game_over(self):
        embed = discord.Embed(color=EMBED_COLOR)
        embed.description = (
            "˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ\n"
            f"the word was: {self.word}\n"
            "use /gamestart to play again"
        )
        await self.channel.send(embed=embed)

        self.word = ""
        if self.timer_task:
            self.timer_task.cancel()

    # ===== Message listener =====
    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.word:
            return
        if message.author.bot:
            return
        if message.channel != self.channel:
            return

        await self.process_guess(message.author.name, message.content)


async def setup(bot):
    await bot.add_cog(Game(bot))