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

        self.round_scores = {}
        self.total_scores = {}

        self.words = self.load_words()

    def load_words(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_words = []
        for cat in data.values():
            all_words.extend(cat)
        return all_words

    # ================= START =================
    @app_commands.command(name="gamestart", description="Start a game")
    async def gamestart(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if self.game_running:
            await interaction.followup.send("A game is already running.", ephemeral=True)
            return

        self.game_running = True
        self.channel = interaction.channel
        self.starter = interaction.user

        self.word_entry = random.choice(self.words)
        self.word = self.word_entry["word"]
        self.word_display = ["⬜"] * len(self.word)

        self.timer = 60
        self.round_scores = {}

        await interaction.followup.send("🎮 Game started!")
        await self.send_embed()

        self.timer_task = asyncio.create_task(self.timer_loop())

    # ================= STOP =================
    @app_commands.command(name="stopgame", description="Stop the game")
    async def stopgame(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not self.game_running:
            await interaction.followup.send("No game running.")
            return

        if interaction.user != self.starter:
            await interaction.followup.send("Only the starter can stop the game.")
            return

        await self.end_game()

    # ================= LEADERBOARD =================
    @app_commands.command(name="leaderboard", description="Show leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not self.total_scores:
            await interaction.followup.send("No scores yet.")
            return

        lines = []
        for user, score in sorted(self.total_scores.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"🏆 {user}: {score}")

        embed = discord.Embed(title="Leaderboard", description="\n".join(lines))
        await interaction.followup.send(embed=embed)

    # ================= TIMER =================
    async def timer_loop(self):
        try:
            while self.timer > 0 and self.game_running:
                await asyncio.sleep(1)
                self.timer -= 1
                if self.timer in (30, 15):
                    await self.channel.send(f"⏳ {self.timer} seconds remaining")

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

        valid = [normalize(w["word"]) for w in self.words]
        if guess not in valid:
            return

        colors = []
        for i, c in enumerate(guess):
            if i < len(target):
                if c == target[i]:
                    colors.append("🟩")
                elif c in target:
                    colors.append("🟨")
                else:
                    colors.append("⬛")
            else:
                colors.append("⬛")

        await self.channel.send("".join(colors))

        player = message.author.name

        if guess == target:
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.total_scores[player] = self.total_scores.get(player, 0) + 1

            await self.channel.send(f"🎉 {player} guessed the word!")
            await self.end_game()

    # ================= EMBED =================
    async def send_embed(self):
        embed = discord.Embed(title="Guess the Word")
        embed.add_field(name="Word", value="".join(self.word_display))
        embed.add_field(name="Time", value=f"{self.timer}s")
        embed.add_field(name="Hint", value=self.word_entry.get("start_hint", "No hint"))
        await self.channel.send(embed=embed)

    # ================= END =================
    async def end_game(self):
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

        embed = discord.Embed(title="Game Over", description=f"The word was: **{self.word}**")
        await self.channel.send(embed=embed)

        self.game_running = False
        self.word = ""
        self.word_display = []
        self.starter = None

async def setup(bot):
    await bot.add_cog(Game(bot))