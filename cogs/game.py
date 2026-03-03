import discord
from discord.ext import commands
from discord import app_commands
import json, random, os, asyncio

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel = None
        self.starter_player = None
        self.game_in_progress = False

        self.round = 0
        self.timer = 60
        self.timer_task = None

        self.word_entry = None
        self.word = ""
        self.word_display = []

        self.used_words = []
        self.used_hints = []
        self.hearts = 5

        self.round_scores = {}
        self.total_scores = {}

        self.words = self.load_words()

    def load_words(self):
        path = os.path.join(os.path.dirname(__file__), "../data/words.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["All"]

    def normalize(self, text: str):
        return "".join(text.lower().split())

    # ================== START GAME ==================
    @app_commands.command(name="gamestart")
    async def gamestart(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if self.game_in_progress:
            await interaction.followup.send("A game is already running.", ephemeral=True)
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
        if not choices:
            self.used_words.clear()
            choices = self.words.copy()

        self.word_entry = random.choice(choices)
        self.word = self.word_entry["word"].upper()
        self.used_words.append(self.word)
        if len(self.used_words) > 5:
            self.used_words.pop(0)

        self.word_display = ["⬜"] * len(self.word)

        await interaction.followup.send("Game started!")
        await self.send_round_embed()

        self.timer_task = asyncio.create_task(self.timer_countdown())

    # ================== STOP GAME ==================
    @app_commands.command(name="stopgame")
    async def stopgame(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not self.game_in_progress:
            await interaction.followup.send("No game is running.")
            return

        if interaction.user != self.starter_player:
            await interaction.followup.send("Only the player who started the game can stop it.")
            return

        await self.end_game()

    # ================== LEADERBOARD ==================
    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not self.total_scores:
            await interaction.followup.send("No scores yet.")
            return

        lines = []
        for user, score in sorted(self.total_scores.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"🏆 {user}: {score} points")

        embed = discord.Embed(title="Leaderboard", description="\n".join(lines), color=0x1b1c23)
        await interaction.followup.send(embed=embed)

    # ================== TIMER ==================
    async def timer_countdown(self):
        try:
            while self.timer > 0 and self.game_in_progress:
                await asyncio.sleep(1)
                self.timer -= 1
                if self.timer in (30, 15):
                    await self.channel.send(f"⏳ {self.timer} seconds remaining")

            if self.game_in_progress:
                await self.game_over()
        except asyncio.CancelledError:
            return

    # ================== MESSAGE LISTENER ==================
    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.game_in_progress:
            return
        if message.author.bot:
            return
        if message.channel != self.channel:
            return

        guess = self.normalize(message.content)
        target = self.normalize(self.word)

        valid_words = [self.normalize(w["word"]) for w in self.words]

        if guess not in valid_words:
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
            await self.send_mini_leaderboard()
            await self.game_over()

    # ================== EMBEDS ==================
    async def send_round_embed(self):
        embed = discord.Embed(color=0x1b1c23)
        embed.title = f"Guess the Word — Round {self.round}"
        embed.add_field(name="Time", value=f"{self.timer}s", inline=False)
        embed.add_field(name="Word", value="".join(self.word_display), inline=False)
        embed.add_field(name="Starter Hint", value=self.word_entry["start_hint"], inline=False)
        await self.channel.send(embed=embed)

    async def send_mini_leaderboard(self):
        if not self.round_scores:
            return
        lines = []
        for user, score in sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"{user}: {score}")
        embed = discord.Embed(title="Mini Leaderboard", description="\n".join(lines), color=0x1b1c23)
        await self.channel.send(embed=embed)

    # ================== END GAME ==================
    async def game_over(self):
        embed = discord.Embed(color=0x1b1c23)
        embed.add_field(name="Game Over", value=f"The word was: **{self.word}**", inline=False)
        await self.channel.send(embed=embed)
        await self.end_game()

    async def end_game(self):
        self.game_in_progress = False
        self.word = ""
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

# ================== SETUP ==================
async def setup(bot):
    await bot.add_cog(Game(bot))