import discord
from discord.ext import commands
from discord import app_commands
import random, json, os, asyncio

EMBED_COLOR = discord.Color.from_rgb(27, 28, 35)
ROUND_TIME = 60

BASE_DIR = os.path.dirname(__file__)
WORDS_PATH = os.path.join(BASE_DIR, "..", "data", "words.json")
LEADERBOARD_PATH = os.path.join(BASE_DIR, "..", "data", "leaderboard.json")

with open(WORDS_PATH, "r", encoding="utf-8") as f:
    WORDS = json.load(f)["All"]

if not os.path.exists(LEADERBOARD_PATH):
    with open(LEADERBOARD_PATH, "w") as f:
        json.dump({}, f)

def load_leaderboard():
    with open(LEADERBOARD_PATH, "r") as f:
        return json.load(f)

def save_leaderboard(data):
    with open(LEADERBOARD_PATH, "w") as f:
        json.dump(data, f, indent=2)

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.channel = None
        self.word = ""
        self.hints = []
        self.used_hints = []
        self.display = []
        self.time_left = 0
        self.message = None
        self.round_scores = {}
        self.streaks = {}
        self.timer_task = None
        self.double_points_users = set()

    # ---------------- /gamestart ---------------- #
    @app_commands.command(name="gamestart", description="Start Guess the Word")
    async def gamestart(self, interaction: discord.Interaction):
        if self.running:
            await interaction.response.send_message("Game already running.", ephemeral=True)
            return

        self.running = True
        self.channel = interaction.channel
        self.round_scores.clear()
        self.double_points_users.clear()
        await interaction.response.send_message("🎮 Game started!")
        await self.new_round()

    # ---------------- NEW ROUND ---------------- #
    async def new_round(self):
        data = random.choice(WORDS)
        self.word = data["word"].upper()
        self.hints = [data["start_hint"], data["hint1"], data["hint2"], data["hint3"]]
        self.used_hints = []
        self.display = ["⬜" if c != " " else " " for c in self.word]
        self.time_left = ROUND_TIME

        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.timer_loop())

        await self.send_embed()

    # ---------------- TIMER ---------------- #
    async def timer_loop(self):
        while self.time_left > 0:
            await asyncio.sleep(1)
            self.time_left -= 1

            if self.time_left in (30, 15):
                await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.time_left} seconds remaining ⠀ּ ּ ✧")

            await self.send_embed()

        await self.game_over()

    # ---------------- WORDLE PROCESS ---------------- #
    def process_guess(self, guess):
        guess = guess.upper()
        result = ["⬛"] * len(self.word)
        word_copy = list(self.word)

        for i, ch in enumerate(guess):
            if ch == self.word[i]:
                result[i] = "🟩"
                word_copy[i] = None

        for i, ch in enumerate(guess):
            if result[i] == "🟩":
                continue
            if ch in word_copy:
                result[i] = "🟨"
                word_copy[word_copy.index(ch)] = None
            else:
                result[i] = "⬛"

        self.display = result

    def wordle_display(self):
        return "".join(self.display)

    # ---------------- MINI LEADERBOARD ---------------- #
    def mini_leaderboard(self):
        if not self.round_scores:
            return ""
        lines = []
        sorted_scores = sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (name, pts) in enumerate(sorted_scores):
            trophy = "<:CC_trophy:1474577678790299821> " if i == 0 else ""
            lines.append(f"◡◡  {trophy}{name} : {pts} Points ♡  ࣪")
        return "\n".join(lines)

    # ---------------- SEND EMBED ---------------- #
    async def send_embed(self):
        if self.message:
            try:
                await self.message.delete()
            except:
                pass

        desc = f"""
Word:
{self.wordle_display()}

⠀♡⃕⠀⠀Timer 𓂃　۪ ׄ
{self.time_left}s

Starter Hint:
{self.hints[0]}

Used Hints:
{"None" if not self.used_hints else " • ".join(self.used_hints)}

{self.mini_leaderboard()}
"""

        embed = discord.Embed(description=desc, color=EMBED_COLOR)
        self.message = await self.channel.send(embed=embed)

    # ---------------- IGNORE NORMAL CHAT ---------------- #
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.running:
            return
        if message.author.bot:
            return
        if message.channel != self.channel:
            return

        guess = message.content.strip().upper()

        if len(guess) != len(self.word):
            return

        self.process_guess(guess)
        await self.send_embed()

        if guess != self.word:
            return

        name = message.author.display_name
        points = 2 if message.author.id in self.double_points_users else 1

        self.round_scores[name] = self.round_scores.get(name, 0) + points
        self.streaks[name] = self.streaks.get(name, 0) + 1

        leaderboard = load_leaderboard()
        leaderboard[name] = leaderboard.get(name, 0) + points
        save_leaderboard(leaderboard)

        if self.streaks[name] % 3 == 0:
            await self.channel.send(f"🔥 {name} earned a streak reward: +1 free hint!")

        await self.channel.send(f"🎉 {name} got it correct!")
        self.double_points_users.clear()
        await self.new_round()

    # ---------------- /hint ---------------- #
    @app_commands.command(name="hint", description="Get a hint")
    async def hint(self, interaction: discord.Interaction):
        if not self.running:
            await interaction.response.send_message("No game running.", ephemeral=True)
            return

        if len(self.used_hints) >= 3:
            await interaction.response.send_message("No more hints.", ephemeral=True)
            return

        hint = self.hints[len(self.used_hints) + 1]
        self.used_hints.append(hint)
        await interaction.response.send_message(f"Hint: {hint}")
        await self.send_embed()

    # ---------------- /revealletter ---------------- #
    @app_commands.command(name="revealletter", description="Reveal one letter")
    async def revealletter(self, interaction: discord.Interaction):
        for i, c in enumerate(self.word):
            if self.display[i] == "⬜" and c != " ":
                self.display[i] = "🟩"
                break
        await interaction.response.send_message("♡⠀⠀⠀⠀Power Ups⠀⠀\n/revealletter")
        await self.send_embed()

    # ---------------- /doublepoints ---------------- #
    @app_commands.command(name="doublepoints", description="Double your next correct guess")
    async def doublepoints(self, interaction: discord.Interaction):
        self.double_points_users.add(interaction.user.id)
        await interaction.response.send_message("♡⠀⠀⠀⠀Power Ups⠀⠀\n/doublepoints")

    # ---------------- /leaderboard ---------------- #
    @app_commands.command(name="leaderboard", description="Show the global leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        leaderboard = load_leaderboard()

        if not leaderboard:
            await interaction.response.send_message("No scores yet.", ephemeral=True)
            return

        sorted_scores = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

        lines = []
        for i, (name, pts) in enumerate(sorted_scores[:10]):
            trophy = "<:CC_trophy:1474577678790299821> " if i == 0 else ""
            lines.append(f"◡◡  {trophy}{name} : {pts} Points ♡  ࣪")

        embed = discord.Embed(
            description="\n".join(lines),
            color=EMBED_COLOR
        )

        await interaction.response.send_message(embed=embed)

    # ---------------- GAME OVER ---------------- #
    async def game_over(self):
        self.running = False
        if self.message:
            try:
                await self.message.delete()
            except:
                pass

        text = "˚⠀⠀♡⃕⠀⠀Game Over 𓂃　۪ ׄ\n\n"
        for name, pts in sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True):
            text += f"{name} - {pts} points\n"

        await self.channel.send(text)

async def setup(bot):
    await bot.add_cog(Game(bot))