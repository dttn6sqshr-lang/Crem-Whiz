import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import asyncio

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}   # {guild_id: game_data}
        self.timers = {}  # {guild_id: asyncio.Task}
        self.scores = {}  # {user_id: total_points}

        # Load words
        with open("data/words.json", "r", encoding="utf-8") as f:
            self.words = json.load(f)

        # Hidden difficulties (points per word)
        self.difficulties = [
            {"points": 1},  # Very Easy
            {"points": 2},  # Easy
            {"points": 3},  # Medium
            {"points": 4},  # Hard
            {"points": 5},  # Very Hard
            {"points": 6},  # Extreme
        ]

    # ----- Category dropdown -----
    class CategorySelect(discord.ui.Select):
        def __init__(self, categories, cog):
            self.cog = cog
            options = [discord.SelectOption(label=c, description=f"Play {c}") for c in categories]
            super().__init__(placeholder="Choose a category...", options=options)

        async def callback(self, interaction: discord.Interaction):
            category = self.values[0]
            await self.cog.start_round(interaction, category, interaction.user)

    class CategoryView(discord.ui.View):
        def __init__(self, categories, cog):
            super().__init__()
            self.add_item(Game.CategorySelect(categories, cog))

    # ----- /startgame -----
    @app_commands.command(name="startgame", description="Start a Crème Whiz game")
    async def startgame(self, interaction: discord.Interaction):
        view = Game.CategoryView(self.words.keys(), self)
        await interaction.response.send_message("Choose a category:", view=view)

    # ----- /hint command -----
    @app_commands.command(name="hint", description="Use a hint (costs 1 point)")
    async def hint(self, interaction: discord.Interaction):
        game = self.games.get(interaction.guild_id)
        if not game:
            await interaction.response.send_message(
                "❌ No game running. Use /startgame first.", ephemeral=True
            )
            return

        # Deduct 1 point from user
        user_id = interaction.user.id
        self.scores[user_id] = self.scores.get(user_id, 0)
        if self.scores[user_id] > 0:
            self.scores[user_id] -= 1

        answer = game["word"]
        revealed = ["_" for _ in answer]
        revealed[0] = answer[0]  # always reveal first letter
        unrevealed = [i for i, l in enumerate(revealed) if l == "_"]
        if unrevealed:
            idx = random.choice(unrevealed)
            revealed[idx] = answer[idx]

        hint_display = " ".join(revealed)
        await interaction.response.send_message(
            f"💡 Hint (costs 1 point): {hint_display}\n"
            f"🏆 Your total points: {self.scores[user_id]}"
        )

    # ----- Start a round -----
    async def start_round(self, interaction, category, user):
        entry = random.choice(self.words[category])
        difficulty = random.choice(self.difficulties)
        guild_id = interaction.guild_id

        self.games[guild_id] = {
            "word": entry["word"].upper(),
            "hint": entry["hint"],
            "guesses": 3,
            "points": difficulty["points"],
            "user": user,
            "category": category  # store category for continuous words
        }

        # Start 1.5-minute timer
        if guild_id in self.timers:
            self.timers[guild_id].cancel()
        self.timers[guild_id] = self.bot.loop.create_task(
            self.end_game_timer(interaction.channel, guild_id)
        )

        word_len = len(entry["word"])
        await interaction.response.send_message(
            f"🎮 **Crème Whiz Started!**\n"
            f"📚 Category: **{category}**\n"
            f"✏ Word length: **{word_len} letters**\n"
            f"💡 Hint: {entry['hint']}\n"
            f"❤️ Guesses: 3 | Points for this word: {difficulty['points']}\n\n"
            f"Type your guess directly in the channel!\n"
            f"Use `/hint` for extra help! ⏱ 1.5 minutes to guess."
        )

    # ----- Listen for guesses -----
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = message.guild.id
        game = self.games.get(guild_id)
        if not game:
            return

        guess_word = message.content.strip().upper()
        answer = game["word"]

        if len(guess_word) != len(answer):
            return

        # Wordle-style feedback
        feedback = []
        answer_letters = list(answer)
        for i in range(len(guess_word)):
            if guess_word[i] == answer[i]:
                feedback.append("🟩")
                answer_letters[i] = None
            else:
                feedback.append(None)
        for i in range(len(guess_word)):
            if feedback[i] is None:
                if guess_word[i] in answer_letters:
                    feedback[i] = "🟨"
                    answer_letters[answer_letters.index(guess_word[i])] = None
                else:
                    feedback[i] = "⬛"

        feedback_line = "".join(feedback)
        game["guesses"] -= 1

        # Correct guess
        if guess_word == answer:
            user = game["user"]
            self.scores[user.id] = self.scores.get(user.id, 0) + game["points"]
            await message.channel.send(
                f"🎉 **Correct!** The word was **{answer}**\n{feedback_line}\n"
                f"🏆 You earned **{game['points']} points!**\n"
                f"💰 Total points: {self.scores[user.id]}"
            )
            # Start next word in the SAME category
            await self.start_next_word(message.channel, game["category"], user)
        elif game["guesses"] <= 0:
            await message.channel.send(
                f"💀 Out of guesses! The word was **{answer}**\n{feedback_line}\n"
                f"⚠ You earned 0 points. Use /startgame to start a new category."
            )
            await self.end_game_cleanup(guild_id)
        else:
            await message.channel.send(
                f"{feedback_line}\n💡 Hint: {game['hint']}\n"
                f"❤️ Guesses left: {game['guesses']}"
            )

        await self.bot.process_commands(message)

    # ----- Start next word in same category automatically -----
    async def start_next_word(self, channel, category, user):
        entry = random.choice(self.words[category])
        difficulty = random.choice(self.difficulties)
        guild_id = channel.guild.id

        self.games[guild_id] = {
            "word": entry["word"].upper(),
            "hint": entry["hint"],
            "guesses": 3,
            "points": difficulty["points"],
            "user": user,
            "category": category
        }

        # Start 1.5-minute timer
        if guild_id in self.timers:
            self.timers[guild_id].cancel()
        self.timers[guild_id] = self.bot.loop.create_task(
            self.end_game_timer(channel, guild_id)
        )

        word_len = len(entry["word"])
        await channel.send(
            f"🎮 **Next word!**\n"
            f"📚 Category: **{category}**\n"
            f"✏ Word length: **{word_len} letters**\n"
            f"💡 Hint: {entry['hint']}\n"
            f"❤️ Guesses: 3 | Points for this word: {difficulty['points']}\n"
            f"Type your guess in the channel! ⏱ 1.5 minutes to guess."
        )

    # ----- Timer ends round -----
    async def end_game_timer(self, channel, guild_id):
        await asyncio.sleep(90)  # 1.5 minutes
        game = self.games.get(guild_id)
        if game:
            answer = game["word"]
            await channel.send(
                f"⏰ Time's up! The word was **{answer}**\n"
                f"⚠ You earned 0 points. Use /startgame to start a new category."
            )
            await self.end_game_cleanup(guild_id)

    # ----- Cleanup -----
    async def end_game_cleanup(self, guild_id):
        self.games.pop(guild_id, None)
        timer_task = self.timers.pop(guild_id, None)
        if timer_task:
            timer_task.cancel()


# ----- Cog setup -----
async def setup(bot: commands.Bot):
    await bot.add_cog(Game(bot))