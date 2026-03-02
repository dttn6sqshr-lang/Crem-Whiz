import discord
from discord.ext import commands, tasks
import asyncio
import json
import random

# Load words.json
with open("data/words.json", "r") as f:
    WORDS = json.load(f)["All"]

ROUND_TIME = 60  # seconds per round

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_game = False
        self.round_number = 0
        self.current_word = None
        self.past_guesses = []
        self.guessed_letters = []
        self.hints_used = 0
        self.time_remaining = ROUND_TIME
        self.embed_message = None
        self.round_task = None

        # Scoreboards
        self.mini_scoreboard = {}
        self.leaderboard = {}
        self.guess_streaks = {}
        self.extra_hints = {}
        self.doublepoints_next = {}

    # -------------------- Start Game --------------------
    @commands.command(name="startgame")
    async def start_game(self, ctx):
        if self.active_game:
            await ctx.send("A game is already running!")
            return

        self.active_game = True
        self.round_number = 1
        self.mini_scoreboard.clear()
        self.past_guesses.clear()
        self.guessed_letters.clear()
        self.hints_used = 0
        self.time_remaining = ROUND_TIME
        self.pick_word()
        self.init_round_state()
        await self.update_embed(ctx.channel)
        self.round_task = asyncio.create_task(self.round_timer(ctx.channel))

    # -------------------- Pick Word --------------------
    def pick_word(self):
        self.current_word = random.choice(WORDS)

    # -------------------- Round State --------------------
    def init_round_state(self):
        self.past_guesses = []
        self.guessed_letters = []
        self.hints_used = 0
        self.time_remaining = ROUND_TIME

    # -------------------- Wordle Feedback --------------------
    def wordle_feedback(self, guess):
        guess = guess.upper()
        word = self.current_word["word"].upper()
        word_letters = list(word)
        guess_letters = list(guess)
        result = [""] * len(guess_letters)

        # Correct letter + correct position
        for i, l in enumerate(guess_letters):
            if i < len(word_letters) and l == word_letters[i]:
                result[i] = "🟩"
                word_letters[i] = None

        # Correct letter wrong position
        for i, l in enumerate(guess_letters):
            if result[i] == "":
                if l in word_letters:
                    result[i] = "🟨"
                    word_letters[word_letters.index(l)] = None
                else:
                    result[i] = "⬛"
        return "".join(result)

    # -------------------- Update Embed --------------------
    async def update_embed(self, channel, warning=None):
        # Wordle grid
        word_display = ""
        for guess_user, guess_word, feedback in self.past_guesses:
            word_display += f"{feedback}  ({guess_user})\n"
        word_display += "▪️" * len(self.current_word["word"]) + "\n"

        # Hints
        hints_used_list = []
        if self.hints_used >= 1: hints_used_list.append(f"1️⃣ {self.current_word.get('hint1','No hint')}")
        if self.hints_used >= 2: hints_used_list.append(f"2️⃣ {self.current_word.get('hint2','No hint')}")
        if self.hints_used >= 3: hints_used_list.append(f"3️⃣ {self.current_word.get('hint3','No hint')}")
        hint_display = self.current_word["start_hint"]
        if hints_used_list:
            hint_display += "\n" + "\n".join(hints_used_list)

        # Mini leaderboard
        leaderboard_text = ""
        sorted_players = sorted(self.mini_scoreboard.items(), key=lambda x: x[1], reverse=True)
        top_score = sorted_players[0][1] if sorted_players else 0
        for idx, (player, score) in enumerate(sorted_players, start=1):
            trophy = "<:CC_trophy:1474577678790299821> " if score == top_score and idx == 1 else ""
            leaderboard_text += f"{idx}️⃣ {trophy}{player} – {score} points\n"
        if not leaderboard_text:
            leaderboard_text = "No guesses yet."

        # Hearts / progress
        hearts_display = "❤️" * (5 - self.hints_used) + "🖤" * self.hints_used

        # Footer
        footer_text = f"⏱ {self.time_remaining}s left | 💡 {3 - self.hints_used} hints left"
        streak_notifications = []
        for user, streak in self.guess_streaks.items():
            if streak > 0 and streak % 3 == 0:
                streak_notifications.append(f"🔥 {user} has a {streak}-round streak!")
        if streak_notifications:
            footer_text += " | " + " ".join(streak_notifications)

        embed = discord.Embed(
            title=f"🎮 Guess the Word! – Round {self.round_number}",
            description=f"Word:\n{word_display}\nProgress: {hearts_display}",
            color=discord.Color.green()
        )
        embed.add_field(name="Hints", value=hint_display, inline=False)
        embed.add_field(name="Mini Leaderboard", value=leaderboard_text, inline=False)
        if warning:
            embed.set_footer(text=f"{footer_text} | {warning}")
        else:
            embed.set_footer(text=footer_text)

        # Replace old embed
        if self.embed_message:
            try: await self.embed_message.delete()
            except: pass
        self.embed_message = await channel.send(embed=embed)

    # -------------------- Round Timer --------------------
    async def round_timer(self, channel):
        while self.time_remaining > 0:
            await asyncio.sleep(1)
            self.time_remaining -= 1
            # Send 30s / 15s warnings
            if self.time_remaining in [30, 15]:
                await self.update_embed(channel, warning=f"{self.time_remaining}s remaining!")
        # Game over
        await channel.send("⏰ Time’s up! Game over. Use `/startgame` to play again.")
        self.active_game = False

    # -------------------- Message Listener --------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not self.active_game or not self.current_word:
            return
        user = message.author.name
        guess = message.content.strip().upper()
        valid_words = {w.upper() for w in WORDS if " " in w or len(w.split()) == 1}
        if guess not in valid_words:
            return  # Ignore chat messages

        feedback = self.wordle_feedback(guess)
        self.past_guesses.append((user, guess, feedback))

        if guess == self.current_word["word"].upper():
            # Award points
            points = 1
            if self.doublepoints_next.get(user):
                points *= 2
                self.doublepoints_next[user] = False
            self.mini_scoreboard[user] = self.mini_scoreboard.get(user, 0) + points
            self.leaderboard[user] = self.leaderboard.get(user, 0) + points

            # Streaks
            self.guess_streaks[user] = self.guess_streaks.get(user, 0) + 1
            if self.guess_streaks[user] % 3 == 0:
                self.extra_hints[user] = self.extra_hints.get(user, 0) + 1
                self.doublepoints_next[user] = True
                await message.channel.send(f"🔥 {user} has a {self.guess_streaks[user]}-round streak! +1 extra hint & double points next guess!")

            # Reset round
            if self.round_task:
                self.round_task.cancel()
            self.round_number += 1
            self.pick_word()
            self.init_round_state()
            await self.update_embed(message.channel)
            self.round_task = asyncio.create_task(self.round_timer(message.channel))
            await message.channel.send(f"🎉 {user} guessed correctly! Next round started.")
        else:
            await self.update_embed(message.channel)

def setup(bot):
    bot.add_cog(Game(bot))