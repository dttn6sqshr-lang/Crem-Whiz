import discord
from discord.ext import commands
from discord import app_commands
import json, random, os, asyncio, re

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/words.json")

def normalize(text: str):
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
        self.last_guess_colors = ""

        self.timer = 60
        self.timer_task = None
        self.round = 0

        self.used_hints = []
        self.round_scores = {}
        self.total_scores = {}

        self.recent_words = []

        self.words = self.load_words()
        print("Loaded words:", len(self.words))

    # ===== LOAD WORDS =====
    def load_words(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        all_words = []
        for category in data.values():
            if isinstance(category, list):
                for item in category:
                    if isinstance(item, dict) and "word" in item:
                        all_words.append(item)
        return all_words

    # ================= START =================
    @app_commands.command(name="gamestart", description="Start Guess the Word")
    async def gamestart(self, interaction: discord.Interaction):
        if self.game_running:
            await interaction.response.send_message("A game is already running.", ephemeral=True)
            return

        await interaction.response.send_message("🎮 Starting game...", ephemeral=True)

        self.game_running = True
        self.channel = interaction.channel
        self.starter = interaction.user

        self.round_scores = {}
        self.last_guess_colors = ""
        self.timer = 60
        self.round = 0

        await self.start_new_round()

    # ================= STOP =================
    @app_commands.command(name="stopgame", description="Stop the game")
    async def stopgame(self, interaction: discord.Interaction):
        if not self.game_running:
            await interaction.response.send_message("No game running.", ephemeral=True)
            return

        if interaction.user != self.starter:
            await interaction.response.send_message("Only the starter can stop the game.", ephemeral=True)
            return

        await interaction.response.send_message("🛑 Game stopped.", ephemeral=True)
        await self.end_game(manual=True)

    # ================= LEADERBOARD =================
    @app_commands.command(name="leaderboard", description="Show leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        if not self.total_scores:
            await interaction.response.send_message("No scores yet.")
            return

        lines = []
        for user, score in sorted(self.total_scores.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"◡◡ 🏆 {user} : {score} Points ♡")

        embed = discord.Embed(color=0x1b1c23, description="\n".join(lines))
        await interaction.response.send_message(embed=embed)

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
        if message.author.bot:
            return
        if message.channel != self.channel:
            return

        guess = normalize(message.content)
        target = normalize(self.word)

        valid_words = [normalize(w["word"]) for w in self.words]
        if guess not in valid_words:
            return

        # Wordle coloring
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

        self.last_guess_colors = "".join(colors)
        await self.send_round_embed()

        # Correct guess → points + new word
        if guess == target:
            player = message.author.name
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.total_scores[player] = self.total_scores.get(player, 0) + 1

            await self.send_mini_leaderboard()
            await self.channel.send(f"🎉 {player} guessed the word!")

            await self.start_new_round()

    # ================= NEW ROUND =================
    async def start_new_round(self):
        self.round += 1

        choices = [w for w in self.words if w["word"] not in self.recent_words]
        if not choices:
            self.recent_words = []
            choices = self.words

        self.word_entry = random.choice(choices)
        self.word = self.word_entry["word"]
        self.word_display = ["⬜"] * len(self.word)
        self.last_guess_colors = ""
        self.used_hints = []

        # update recent words
        self.recent_words.append(self.word)
        if len(self.recent_words) > 3:
            self.recent_words.pop(0)

        # ===== RESET TIMER =====
        self.timer = 60
        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.timer_loop())

        await self.send_round_embed()

    # ================= ROUND EMBED =================
    async def send_round_embed(self):
        word_line = self.last_guess_colors if self.last_guess_colors else "".join(self.word_display)
        streak = max(self.round_scores.values(), default=0)

        embed = discord.Embed(color=0x1b1c23)
        embed.description = (
            f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟ Round {self.round} ꒱ᣟᣟ\n"
            f"﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚ | {self.timer}s\n"
            f"♩  ﹒ ﹒  Streak  ﹒ ୨୧ | 🔥 {streak}\n\n"
            f"{word_line}\n\n"
            f"⃕⠀⠀Timer 𓂃　۪ ׄ\n"
            f"{'❤️'*5}\n\n"
            f"⃕⠀⠀starter hint 𓂃　۪ ׄ\n{self.word_entry.get('start_hint','No hint')}\n\n"
            f"⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ\n{'None' if not self.used_hints else '\\n'.join(self.used_hints)}"
        )
        await self.channel.send(embed=embed)

    # ================= MINI LEADERBOARD =================
    async def send_mini_leaderboard(self):
        lines = []
        for player, score in sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"◡◡ 🏆 {player} : {score} Points ♡")

        embed = discord.Embed(color=0x1b1c23, description="\n".join(lines))
        await self.channel.send(embed=embed)

    # ================= END =================
    async def end_game(self, manual=False):
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

        embed = discord.Embed(color=0x1b1c23)
        embed.add_field(
            name="˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ",
            value=f"The word was: **{self.word}**\nUse /gamestart to play again",
            inline=False,
        )
        await self.channel.send(embed=embed)

        self.reset_game()

    # ================= RESET =================
    def reset_game(self):
        self.game_running = False
        self.word = ""
        self.word_entry = None
        self.word_display = []
        self.channel = None
        self.starter = None
        self.used_hints = []
        self.round_scores = {}
        self.last_guess_colors = ""
        self.round = 0

async def setup(bot):
    await bot.add_cog(Game(bot))