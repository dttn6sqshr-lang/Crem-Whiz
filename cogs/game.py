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

        self.word_entry = None
        self.word = ""
        self.word_display = []
        self.timer = 60
        self.timer_task = None

        self.round_scores = {}
        self.total_scores = {}
        self.streaks = {}
        self.used_hints = []
        self.recent_words = []

        self.words = self.load_words()

    def load_words(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_words = []
        for cat in data.values():
            all_words.extend(cat)
        return all_words

    # ================= START =================
    @app_commands.command(name="gamestart", description="Start a Guess the Word game")
    async def gamestart(self, interaction: discord.Interaction):
        if self.game_running:
            await interaction.response.send_message("A game is already running!", ephemeral=True)
            return

        self.game_running = True
        self.channel = interaction.channel
        self.starter = interaction.user

        # Pick a new word not in recent_words
        choices = [w for w in self.words if w["word"] not in self.recent_words]
        if not choices:
            self.recent_words = []
            choices = self.words
        self.word_entry = random.choice(choices)
        self.word = self.word_entry["word"]
        self.word_display = ["⬜"] * len(self.word)
        self.recent_words.append(self.word)
        if len(self.recent_words) > 3:
            self.recent_words.pop(0)

        self.round_scores = {}
        self.used_hints = []
        self.timer = 60

        # Send first round embed
        await self.send_round_embed()

        # Respond to interaction
        await interaction.response.send_message("🎮 Game started! Check the channel for the round.", ephemeral=True)

        # Start timer loop in background
        self.timer_task = asyncio.create_task(self.timer_loop())

    # ================= STOP =================
    @app_commands.command(name="stopgame", description="Stop the game")
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
    @app_commands.command(name="leaderboard", description="Show total leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not self.total_scores:
            await interaction.followup.send("No scores yet.", ephemeral=True)
            return
        lines = [f"◡◡  <:CC_trophy:1474577678790299821> {u}: {s} Points ♡  ࣪"
                 for u, s in sorted(self.total_scores.items(), key=lambda x: x[1], reverse=True)]
        embed = discord.Embed(title="Leaderboard", description="\n".join(lines), color=0x1b1c23)
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
        if not self.game_running or message.author.bot or message.channel != self.channel:
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

        # Correct guess
        if guess == target:
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.total_scores[player] = self.total_scores.get(player, 0) + 1
            self.streaks[player] = self.streaks.get(player, 0) + 1
            await self.channel.send(f"🎉 {player} guessed the word! 🔥 Streak: {self.streaks[player]}")
            await self.send_mini_leaderboard()
            await self.end_game()
        else:
            self.streaks[player] = 0
            await self.send_round_embed()

    # ================= ROUND EMBED =================
    async def send_round_embed(self):
        embed = discord.Embed(color=0x1b1c23)
        embed.title = f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟᰍᣟᣟᣟ⡟ᣟᣟᣟ꒰ Round 1 ꒱ᣟᣟᣟ꒱"
        embed.add_field(name="﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚", value=f"﹒🍥﹒ᣟᣟ {self.timer}s ᣟᣟᣟ﹒♡﹒ᣟᣟ˚", inline=False)
        streak_display = max(self.streaks.values(), default=0)
        embed.add_field(name="♩  ﹒ ﹒  Streak  ﹒ ୨୧", value=f"ᣟ♩ᣟᣟ﹒ᣟ﹒ᣟ 🔥 {streak_display} ᣟ﹒ᣟ୨୧", inline=False)
        embed.add_field(name="▪️▪️▪️▪️▪️", value="".join(self.word_display), inline=False)
        hearts_display = "❤️" * 5 + "🖤" * (5 - 5)
        embed.add_field(name="⃕⠀⠀Timer 𓂃　۪ ׄ", value=hearts_display, inline=False)
        embed.add_field(name="⃕⠀⠀starter hint 𓂃　۪ ׄ", value=self.word_entry.get("start_hint", "No hint"), inline=False)
        embed.add_field(name="⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ", value="\n".join(self.used_hints) or "None", inline=False)
        await self.channel.send(embed=embed)

    # ================= MINI LEADERBOARD =================
    async def send_mini_leaderboard(self):
        lines = [f"◡◡  <:CC_trophy:1474577678790299821> {u}: {s} Points ♡  ࣪"
                 for u, s in sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True)]
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

        # Reset game state
        self.game_running = False
        self.channel = None
        self.starter = None
        self.word_entry = None
        self.word = ""
        self.word_display = []
        self.round_scores = {}
        self.used_hints = []
        self.streaks = {}

async def setup(bot):
    await bot.add_cog(Game(bot))