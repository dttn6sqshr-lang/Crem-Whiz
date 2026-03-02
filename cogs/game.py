import discord
from discord.ext import commands
import json
import random
from collections import defaultdict

# Load all words from the JSON file
with open("data/words.json", "r") as f:
    WORDS = json.load(f)

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_word = None
        self.hints_used = 0
        self.previous_word = None
        self.mini_scoreboard = defaultdict(int)
        self.leaderboard = defaultdict(int)

    def start_new_round(self):
        """Pick a random word avoiding the previous one and reset hints."""
        if not WORDS:
            return "No words available!"
        new_word = random.choice(WORDS)
        while new_word == self.previous_word and len(WORDS) > 1:
            new_word = random.choice(WORDS)
        self.current_word = new_word
        self.previous_word = new_word
        self.hints_used = 0
        return self.current_word["start_hint"]

    def next_hint(self):
        """Return the next hint for the current word and increment hint counter."""
        self.hints_used += 1
        if self.hints_used == 1:
            return self.current_word.get("hint1", "No more hints!")
        elif self.hints_used == 2:
            return self.current_word.get("hint2", "No more hints!")
        elif self.hints_used == 3:
            return self.current_word.get("hint3", "No more hints!")
        else:
            return "No more hints!"

    def check_answer(self, answer):
        """Check if the player's answer is correct."""
        if not self.current_word:
            return False
        return self.current_word["word"].lower() == answer.lower()

    def get_points(self):
        """Calculate points based on difficulty and hints used."""
        difficulty = self.current_word.get("difficulty", 1)
        # Ensure points are at least 1
        return max(1, difficulty - self.hints_used)

    @commands.command()
    async def startgame(self, ctx):
        """Start a new game round and reset mini scoreboard."""
        self.mini_scoreboard.clear()
        hint = self.start_new_round()
        await ctx.send(f"🎮 New round started! Here's your first hint:\n**{hint}**")

    @commands.command()
    async def hint(self, ctx):
        """Give the next hint for the current word."""
        if not self.current_word:
            await ctx.send("No active round. Use /startgame to begin!")
            return
        hint_text = self.next_hint()
        await ctx.send(f"💡 Hint: {hint_text}")

    @commands.command()
    async def answer(self, ctx, *, guess):
        """Check a player's guess and update scores."""
        user = ctx.author.name
        if not self.current_word:
            await ctx.send("No active round. Use /startgame to begin!")
            return
        if self.check_answer(guess):
            points = self.get_points()
            self.mini_scoreboard[user] += points
            self.leaderboard[user] += points
            correct_word = self.current_word["word"]
            new_hint = self.start_new_round()
            await ctx.send(
                f"✅ Correct, {user}! You earned {points} point(s).\n"
                f"📊 Mini Score: {self.mini_scoreboard[user]}\n"
                f"🏆 Leaderboard: {self.leaderboard[user]}\n"
                f"Next round! Here's your first hint:\n**{new_hint}**"
            )
        else:
            await ctx.send(f"❌ Incorrect, {user}! Try again.")

    @commands.command()
    async def miniscore(self, ctx):
        """Show the mini scoreboard."""
        user = ctx.author.name
        score = self.mini_scoreboard.get(user, 0)
        await ctx.send(f"📊 {user} - Mini Score: {score}")

    @commands.command()
    async def leaderboard(self, ctx):
        """Show the total leaderboard."""
        if not self.leaderboard:
            await ctx.send("Leaderboard is empty.")
            return
        sorted_lb = sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True)
        leaderboard_text = "\n".join([f"{user}: {score}" for user, score in sorted_lb])
        await ctx.send(f"🏆 Leaderboard:\n{leaderboard_text}")