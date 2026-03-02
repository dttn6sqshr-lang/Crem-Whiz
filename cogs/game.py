import discord
from discord.ext import commands
import json
import random
import asyncio

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.words_data = self.load_words()
        self.current_word = None
        self.current_category = "All"
        self.round_timer = 30  # seconds per round
        self.game_active = False
        self.guesses = {}  # user.id -> guesses left for current word
        self.round_scores = {}  # user.id -> points for current round
        self.leaderboard = {}  # user.id -> total points
        self.hints_used = 0
        self.round_task = None

    def load_words(self):
        with open("data/words.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def pick_word(self, category):
        return random.choice(self.words_data[category])

    async def start_round_timer(self, ctx):
        await asyncio.sleep(self.round_timer)
        if self.current_word:
            await ctx.send(f"⏰ Time's up! Moving to the next word.")
            await self.next_word(ctx)

    async def next_word(self, ctx):
        if not self.game_active:
            return

        self.current_word = self.pick_word(self.current_category)
        self.guesses = {}
        self.round_scores = {}
        self.hints_used = 0

        await ctx.send(f"**New word!** Hint: {self.current_word['start_hint']}")

        # Cancel previous timer if exists
        if self.round_task:
            self.round_task.cancel()
        self.round_task = self.bot.loop.create_task(self.start_round_timer(ctx))

    @commands.command()
    async def startgame(self, ctx, category: str = "All"):
        if category not in self.words_data:
            await ctx.send(f"Category `{category}` not found. Available: {', '.join(self.words_data.keys())}")
            return

        self.current_category = category
        self.game_active = True
        self.guesses = {}
        self.round_scores = {}

        await ctx.send(f"🎮 Starting game in category: {category}")
        await self.next_word(ctx)

    @commands.command()
    async def hint(self, ctx):
        if not self.current_word:
            await ctx.send("No active word!")
            return

        if self.hints_used >= 3:
            await ctx.send("All hints used for this word!")
            return

        self.hints_used += 1
        hint_text = self.current_word[f"hint{self.hints_used}"]
        await ctx.send(f"💡 Hint {self.hints_used}: {hint_text}")

    @commands.command()
    async def score(self, ctx):
        if not self.round_scores:
            await ctx.send("No scores yet this round.")
            return
        msg = "**Current Round Scores:**\n"
        for user_id, points in self.round_scores.items():
            user = self.bot.get_user(user_id)
            if user:
                msg += f"{user.name} - {points} points\n"
        await ctx.send(msg)

    @commands.command()
    async def leaderboard(self, ctx):
        if not self.leaderboard:
            await ctx.send("No leaderboard yet.")
            return
        msg = "**Global Leaderboard:**\n"
        sorted_lb = sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True)
        for user_id, points in sorted_lb:
            user = self.bot.get_user(user_id)
            if user:
                msg += f"{user.name} - {points} points\n"
        await ctx.send(msg)

    @commands.command()
    async def stopgame(self, ctx):
        self.game_active = False
        self.current_word = None
        self.guesses = {}
        self.round_scores = {}
        self.hints_used = 0
        if self.round_task:
            self.round_task.cancel()
        await ctx.send("🛑 Game stopped.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not self.game_active or not self.current_word:
            return

        user_id = message.author.id
        guess = message.content.strip().upper()

        # Initialize remaining guesses per player
        if user_id not in self.guesses:
            self.guesses[user_id] = 3  # each player gets 3 guesses per word

        # Check guess
        if guess == self.current_word["word"]:
            # Calculate points: difficulty minus hints used
            points = max(self.current_word["difficulty"] - self.hints_used, 1)
            self.round_scores[user_id] = self.round_scores.get(user_id, 0) + points
            self.leaderboard[user_id] = self.leaderboard.get(user_id, 0) + points

            await message.channel.send(f"✅ {message.author.mention} guessed correctly! +{points} points")
            await self.next_word(message.channel)

        else:
            # Wrong guess: decrease remaining attempts
            self.guesses[user_id] -= 1
            if self.guesses[user_id] > 0:
                await message.add_reaction("❌")  # optional: mark wrong guess
            else:
                await message.author.send("You are out of guesses for this word!")