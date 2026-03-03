import discord
from discord.ext import commands
from discord import app_commands
import json, random, os, asyncio, re

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/words.json")

def normalize(text):
    return re.sub(r"[^a-zA-Z]", "", text).upper()

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_running = False
        self.channel = None
        self.starter = None

        self.word = ""
        self.word_entry = None
        self.word_display = []

        self.timer = 60
        self.timer_task = None
        self.hearts = 5
        self.used_hints = []

        self.round_scores = {}
        self.total_scores = {}
        self.streaks = {}

        self.recent_words = []
        self.words = self.load_words()
        self.round_number = 0

    def load_words(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_words = []
        for cat in data.values():
            all_words.extend(cat)
        return all_words

    def pick_word(self):
        choices = [w for w in self.words if w["word"] not in self.recent_words]
        if not choices:
            self.recent_words.clear()
            choices = self.words
        word = random.choice(choices)
        self.recent_words.append(word["word"])
        if len(self.recent_words) > 3:
            self.recent_words.pop(0)
        return word

    # ================= START GAME =================
    @app_commands.command(name="gamestart", description="Start a new Guess the Word game")
    async def gamestart(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.game_running:
            await interaction.followup.send("A game is already running.", ephemeral=True)
            return

        self.game_running = True
        self.channel = interaction.channel
        self.starter = interaction.user
        self.round_number += 1

        self.word_entry = self.pick_word()
        self.word = self.word_entry["word"]
        self.word_display = ["⬜"] * len(self.word)

        self.timer = 60
        self.hearts = 5
        self.used_hints = []
        self.round_scores = {}

        await self.channel.send(f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟᰍᣟᣟᣟ⡟ᣟᣟᣟ꒰ Round {self.round_number} ꒱ᣟᣟᣟ꒱")
        await self.send_embed()

        self.timer_task = asyncio.create_task(self.timer_loop())

    # ================= STOP GAME =================
    @app_commands.command(name="stopgame", description="Stop the current game")
    async def stopgame(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.game_running:
            await interaction.followup.send("No game running.", ephemeral=True)
            return
        if interaction.user != self.starter:
            await interaction.followup.send("Only the starter can stop the game.", ephemeral=True)
            return
        await self.end_game()

    # ================= LEADERBOARD =================
    @app_commands.command(name="leaderboard", description="Show global leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not self.total_scores:
            await interaction.followup.send("No scores yet.", ephemeral=True)
            return
        lines = []
        for user, score in sorted(self.total_scores.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"◡◡  <:CC_trophy:1474577678790299821> {user} : {score} Points ♡  ࣪")
        embed = discord.Embed(title="📊 Leaderboard", description="\n".join(lines), color=0x1b1c23)
        await interaction.followup.send(embed=embed)

    # ================= TIMER =================
    async def timer_loop(self):
        try:
            while self.timer > 0 and self.game_running:
                await asyncio.sleep(1)
                self.timer -= 1
                if self.timer in (30, 15):
                    await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.timer} seconds remaining ⠀ּ ּ    ✧")
            if self.game_running:
                await self.end_game()
        except asyncio.CancelledError:
            return

    # ================= MESSAGE LISTENER =================
    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.game_running:
            return
        if message.author.bot or message.channel != self.channel:
            return

        guess = normalize(message.content)
        target = normalize(self.word)
        valid_words = [normalize(w["word"]) for w in self.words]

        if guess not in valid_words:
            return

        # Wordle colors
        colors = []
        for i, c in enumerate(guess):
            if i < len(target):
                if c == target[i]:
                    colors.append("🟩")
                elif c in target:
                    colors.append("🟨")
                else:
                    colors.append("⬜")
            else:
                colors.append("⬜")

        await self.channel.send("".join(colors))

        player = message.author.name

        if guess == target:
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.total_scores[player] = self.total_scores.get(player, 0) + 1
            self.streaks[player] = self.streaks.get(player, 0) + 1

            await self.channel.send(f"🎉 {player} guessed the word! 🔥 Streak: {self.streaks[player]}")
            await self.send_mini_leaderboard()
            await self.end_game()
        else:
            self.hearts -= 1
            self.streaks[player] = 0
            if self.hearts <= 0:
                await self.end_game()
            else:
                await self.send_embed()

    # ================= EMBED =================
    async def send_embed(self):
        embed = discord.Embed(color=0x1b1c23)

        embed.add_field(
            name=f"﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚   |   ﹒🍥﹒ᣟᣟ୧ᣟᣟ {self.timer}s ᣟᣟᣟ﹒♡﹒ᣟᣟ˚",
            value="",
            inline=False
        )

        streak_display = max(self.streaks.values(), default=0)
        embed.add_field(
            name=f"♩  ﹒ ﹒  Streak  ﹒ ୨୧   |   ᣟ♩ᣟᣟ﹒ᣟ﹒ᣟ 🔥 {streak_display} ᣟ﹒ᣟ୨୧",
            value="",
            inline=False
        )

        embed.add_field(
            name="▪️▪️▪️▪️▪️",
            value="".join(self.word_display),
            inline=False
        )

        hearts_display = "❤️" * self.hearts + "🖤" * (5 - self.hearts)
        embed.add_field(name="⃕⠀⠀Timer 𓂃　۪ ׄ", value=hearts_display, inline=False)
        embed.add_field(
            name="⃕⠀⠀starter hint 𓂃　۪ ׄ",
            value=self.word_entry.get("start_hint", "No hint"),
            inline=False
        )
        embed.add_field(
            name="⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ",
            value="\n".join(self.used_hints) or "None",
            inline=False
        )

        await self.channel.send(embed=embed)

    # ================= MINI LEADERBOARD =================
    async def send_mini_leaderboard(self):
        lines = []
        sorted_scores = sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True)
        for player, score in sorted_scores:
            lines.append(f"◡◡  <:CC_trophy:1474577678790299821> {player} : {score} Points ♡  ࣪")
        embed = discord.Embed(title="Mini Leaderboard", description="\n".join(lines) or "No scores yet", color=0x1b1c23)
        await self.channel.send(embed=embed)

    # ================= END GAME =================
    async def end_game(self):
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

        embed = discord.Embed(
            title="˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ",
            description=f"The word was: **{self.word}**\nUse `/gamestart` to play again",
            color=0x1b1c23
        )
        await self.channel.send(embed=embed)

        self.game_running = False
        self.word = ""
        self.word_entry = None
        self.word_display = []
        self.starter = None
        self.hearts = 5
        self.used_hints = []
        self.round_scores = {}

async def setup(bot):
    await bot.add_cog(Game(bot))