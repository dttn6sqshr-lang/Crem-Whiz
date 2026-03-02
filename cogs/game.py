import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import asyncio
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/words.json")

class Game(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.current_game = None
        self.leaderboard = {}  # Persistent overall leaderboard
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            self.words_list = json.load(f)

    # ---------------- Slash Command: Start Game ----------------
    @app_commands.command(name="gamestart", description="Start a new Guess the Word game")
    async def gamestart(self, interaction: discord.Interaction):
        if self.current_game:
            await interaction.response.send_message("A game is already running!", ephemeral=True)
            return

        word_obj = random.choice(self.words_list)
        self.current_game = {
            "channel": interaction.channel,
            "round": 1,
            "streak": 0,
            "hearts": 5,
            "hints_used": [],
            "mini_scores": {},
            "word": word_obj["word"].upper(),
            "starter_hint": word_obj.get("hint1", "No hint available"),
            "timer_task": None,
            "guess_streak": 0
        }

        await interaction.response.send_message("Starting game...", ephemeral=False)
        await self.start_round(interaction.channel)

    # ---------------- Start Round ----------------
    async def start_round(self, channel):
        game = self.current_game
        word_len = len(game["word"])
        masked_word = "▪️" * word_len

        embed = discord.Embed(
            description=self.main_round_aesthetic(game, masked_word),
            color=0x1b1c23
        )
        await channel.send(embed=embed)
        # Start timer task
        game["timer_task"] = self.bot.loop.create_task(self.round_timer(channel, 60))

    # ---------------- Round Timer ----------------
    async def round_timer(self, channel, seconds):
        game = self.current_game
        while seconds > 0:
            if seconds in [30, 15]:
                await channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {seconds} seconds remaining ⠀ּ ּ    ✧")
            await asyncio.sleep(1)
            seconds -= 1
        await self.game_over(channel)

    # ---------------- Game Over ----------------
    async def game_over(self, channel):
        game = self.current_game
        embed = discord.Embed(
            description=f"˚⠀⠀♡⃕⠀⠀Game Over 𓂃　۪ ׄ\nThe word was: {game['word']}\nUse /gamestart to play again",
            color=0x1b1c23
        )
        await channel.send(embed=embed)
        self.current_game = None

    # ---------------- Listen for Guesses ----------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.current_game or message.channel != self.current_game["channel"]:
            return
        if message.author.bot:
            return

        word = self.current_game["word"]
        guess = message.content.upper()

        # Only allow guesses from words.json
        if guess not in [w["word"].upper() for w in self.words_list]:
            return

        feedback = self.wordle_feedback(word, guess)
        masked_word = "".join(feedback)

        if guess == word:
            player = message.author.display_name
            self.current_game["streak"] += 1
            self.current_game["guess_streak"] += 1
            self.current_game["mini_scores"][player] = self.current_game["mini_scores"].get(player, 0) + 1
            self.leaderboard[player] = self.leaderboard.get(player, 0) + 1

            # Automatic streak power-up: extra heart every 3 correct in a row
            if self.current_game["guess_streak"] % 3 == 0:
                self.current_game["hearts"] = min(5, self.current_game["hearts"] + 1)

            # Cancel timer and start next round
            if self.current_game["timer_task"]:
                self.current_game["timer_task"].cancel()

            await message.channel.send(f"{player} got it correct!")
            await asyncio.sleep(1)

            # Start next round
            self.current_game["round"] += 1
            word_obj = random.choice(self.words_list)
            self.current_game["word"] = word_obj["word"].upper()
            self.current_game["starter_hint"] = word_obj.get("hint1", "No hint available")
            self.current_game["hints_used"] = []
            await self.start_round(message.channel)

        else:
            self.current_game["hearts"] -= 1
            if self.current_game["hearts"] <= 0:
                await self.game_over(message.channel)
                return

            # Send updated embed with wordle feedback
            embed = discord.Embed(
                description=self.main_round_aesthetic(self.current_game, masked_word),
                color=0x1b1c23
            )
            await message.channel.send(embed=embed)

    # ---------------- Wordle Feedback ----------------
    def wordle_feedback(self, word, guess):
        feedback = []
        word_chars = list(word)
        guess_chars = list(guess)
        # Correct letter & spot
        for i in range(len(word_chars)):
            if guess_chars[i] == word_chars[i]:
                feedback.append("🟩")
                word_chars[i] = None
                guess_chars[i] = None
            else:
                feedback.append("⬜")
        # Correct letter wrong spot
        for i, g in enumerate(guess_chars):
            if g and g in word_chars:
                feedback[i] = "🟨"
                word_chars[word_chars.index(g)] = None
        return feedback

    # ---------------- Main Round Embed Aesthetic ----------------
    def main_round_aesthetic(self, game, masked_word):
        hearts = "❤️" * game["hearts"] + "🖤" * (5 - game["hearts"])
        mini_lb_text = ""
        for player, score in game["mini_scores"].items():
            crown = " <:CC_trophy:1474577678790299821>" if score == max(game["mini_scores"].values(), default=0) else ""
            mini_lb_text += f"◡◡  {crown} {player} : {score} Points ♡  ࣪\n"

        aesthetic = f"""
ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟᰍᣟᣟᣟ⡡ᣟᣟᣟ꒰ Round {game['round']} ꒱ᣟᣟᣟ꒱
﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚   |   ﹒🍥﹒ᣟᣟ୧ᣟᣟ 60s ᣟᣟᣟ﹒♡﹒ᣟᣟ˚
 ♩  ﹒ ﹒  Streak  ﹒ ୨୧   |   ᣟ♩ᣟᣟ﹒ᣟ﹒ᣟ 🔥 {game['streak']} ᣟ﹒ᣟ୨୧

{masked_word}

⃕⠀⠀Timer 𓂃　۪ ׄ
{hearts}

⃕⠀⠀Starter Hint 𓂃　۪ ׄ
{game['starter_hint']}

⠀♡⃕⠀⠀Used Hints 𓂃　۪ ׄ
{', '.join(game['hints_used'])}

{mini_lb_text}
"""
        return aesthetic

    # ---------------- Slash Command: Leaderboard ----------------
    @app_commands.command(name="leaderboard", description="Show overall leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        if not self.leaderboard:
            await interaction.response.send_message("Leaderboard is empty.", ephemeral=True)
            return
        sorted_lb = sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True)
        text = ""
        for player, score in sorted_lb:
            crown = " <:CC_trophy:1474577678790299821>" if score == sorted_lb[0][1] else ""
            text += f"{crown} {player} : {score} Points\n"
        embed = discord.Embed(description=text, color=0x1b1c23)
        await interaction.response.send_message(embed=embed)

# ---------------- Cog Setup ----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Game(bot))
    try:
        await bot.tree.sync()
        print("Slash commands synced successfully!")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")