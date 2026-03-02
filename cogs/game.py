import discord
from discord.ext import commands, tasks
import json
import random
import asyncio
import os

EMBED_COLOR = discord.Color.from_rgb(27, 28, 35)
ROUND_TIME = 60
HEARTS = 10

path = os.path.join(os.path.dirname(__file__), "..", "data", "words.json")
with open(path, "r", encoding="utf-8") as f:
    WORDS = json.load(f)["All"]

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_running = False
        self.channel = None
        self.current_word = ""
        self.display = []
        self.hints = []
        self.used_hints = []
        self.time_left = ROUND_TIME
        self.message = None
        self.round_scores = {}
        self.global_scores = {}
        self.streaks = {}
        self.round = 1
        self.double_points_users = set()

    # ---------------- START GAME ---------------- #

    @commands.slash_command(name="gamestart")
    async def start_game(self, ctx):
        if self.game_running:
            return await ctx.respond("Game already running!", ephemeral=True)

        self.game_running = True
        self.channel = ctx.channel
        self.round = 1
        self.round_scores.clear()
        await ctx.respond("")

        await self.new_round()

    # ---------------- NEW ROUND ---------------- #

    async def new_round(self):
        data = random.choice(WORDS)
        self.current_word = data["word"].upper()
        self.hints = [data["start_hint"], data["hint1"], data["hint2"], data["hint3"]]
        self.used_hints = []
        self.time_left = ROUND_TIME
        self.double_points_users.clear()

        self.display = ["⬜" if c != " " else " " for c in self.current_word]

        await self.send_embed()
        self.timer_loop.start()

    # ---------------- TIMER ---------------- #

    @tasks.loop(seconds=1)
    async def timer_loop(self):
        self.time_left -= 1

        if self.time_left in (30, 15):
            await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.time_left} seconds remaining ⠀ּ ּ ✧")

        if self.time_left <= 0:
            self.timer_loop.cancel()
            await self.end_game()
            return

        await self.send_embed()

    def heart_timer(self):
        filled = int((self.time_left / ROUND_TIME) * HEARTS)
        return "❤️" * filled + "🖤" * (HEARTS - filled)

    # ---------------- WORDLE DISPLAY ---------------- #

    def wordle_display(self):
        return "".join(self.display)

    def process_guess(self, guess):
        guess = guess.upper()
        new_display = self.display.copy()

        for i, letter in enumerate(guess):
            if i < len(self.current_word):
                if letter == self.current_word[i]:
                    new_display[i] = "🟩"
                elif letter in self.current_word:
                    new_display[i] = "🟨"
                else:
                    new_display[i] = "⬛"

        self.display = new_display

    # ---------------- MINI LEADERBOARD ---------------- #

    def mini_leaderboard(self):
        if not self.round_scores:
            return ""
        lines = []
        sorted_scores = sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True)
        for name, pts in sorted_scores:
            trophy = "<:CC_trophy:1474577678790299821> " if pts == sorted_scores[0][1] else ""
            lines.append(f"◡◡  {trophy}{name} : {pts} Points ♡  ࣪")
        return "\n".join(lines)

    # ---------------- EMBED ---------------- #

    async def send_embed(self):
        if self.message:
            await self.message.delete()

        desc = f"""
Word:
{self.wordle_display()}

⠀♡⃕⠀⠀Timer 𓂃　۪ ׄ
{self.heart_timer()}

Starter Hint:
{self.hints[0]}

Used Hints:
{"None" if not self.used_hints else " • ".join(self.used_hints)}

{self.mini_leaderboard()}
"""
        embed = discord.Embed(description=desc, color=EMBED_COLOR)
        self.message = await self.channel.send(embed=embed)

    # ---------------- MESSAGE LISTENER ---------------- #

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.game_running:
            return
        if message.author.bot:
            return
        if message.channel != self.channel:
            return

        guess = message.content.strip().upper()

        if guess != self.current_word:
            return

        self.timer_loop.cancel()

        name = message.author.display_name
        pts = 2
        if name in self.double_points_users:
            pts *= 2

        self.round_scores[name] = self.round_scores.get(name, 0) + pts
        self.global_scores[name] = self.global_scores.get(name, 0) + pts
        self.streaks[name] = self.streaks.get(name, 0) + 1

        await self.channel.send(f"🎉 {name} got it correct!")

        self.round += 1
        await self.new_round()

    # ---------------- HINT ---------------- #

    @commands.slash_command(name="hint")
    async def hint(self, ctx):
        if not self.game_running:
            return await ctx.respond("No game running.", ephemeral=True)

        if len(self.used_hints) + 1 >= len(self.hints):
            return await ctx.respond("No more hints!", ephemeral=True)

        hint = self.hints[len(self.used_hints) + 1]
        self.used_hints.append(hint)
        await ctx.respond("")

    # ---------------- POWER UPS ---------------- #

    @commands.slash_command(name="revealletter")
    async def reveal_letter(self, ctx):
        if not self.game_running:
            return await ctx.respond("No game running.", ephemeral=True)

        indexes = [i for i, c in enumerate(self.display) if c == "⬜"]
        if not indexes:
            return await ctx.respond("Nothing to reveal.", ephemeral=True)

        i = random.choice(indexes)
        self.display[i] = "🟩"
        await ctx.respond("♡⠀⠀⠀⠀Power Ups⠀⠀\n/revealletter")

    @commands.slash_command(name="doublepoints")
    async def double_points(self, ctx):
        self.double_points_users.add(ctx.author.display_name)
        await ctx.respond("♡⠀⠀⠀⠀Power Ups⠀⠀\n/doublepoints")

    # ---------------- END GAME ---------------- #

    async def end_game(self):
        self.game_running = False
        if self.message:
            await self.message.delete()

        text = "˚⠀⠀♡⃕⠀⠀Game Over 𓂃　۪ ׄ\n\n"
        for name, pts in sorted(self.global_scores.items(), key=lambda x: x[1], reverse=True):
            text += f"{name} - {pts} points\n"

        await self.channel.send(text)