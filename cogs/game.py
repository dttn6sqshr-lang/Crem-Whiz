import discord
from discord.ext import commands
from discord import app_commands
import json
import random

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # {guild_id: game_data}

        # Load words
        with open("data/words.json", "r", encoding="utf-8") as f:
            self.words = json.load(f)

        # Points scaling by difficulty, guesses fixed to 3
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
            entry = random.choice(self.cog.words[category])

            difficulty = random.choice(self.cog.difficulties)

            self.cog.games[interaction.guild_id] = {
                "word": entry["word"].upper(),
                "hint": entry["hint"],
                "guesses": 3,  # fixed guesses
                "points": difficulty["points"],
            }

            word_len = len(entry["word"])
            await interaction.response.send_message(
                f"🎮 **Crème Whiz Started!**\n"
                f"📚 Category: **{category}**\n"
                f"✏ Word length: **{word_len} letters**\n"
                f"💡 Hint: {entry['hint']}\n"
                f"❤️ Guesses: 3 | Points: {difficulty['points']}\n\n"
                f"Type your guess directly in the channel!\n"
                f"Use `/hint` for extra help!"
            )

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

        if game["points"] <= 0:
            await interaction.response.send_message(
                "❌ You have no points left to use a hint!", ephemeral=True
            )
            return

        game["points"] -= 1

        answer = game["word"]
        revealed = ["_" for _ in answer]
        revealed[0] = answer[0]

        unrevealed = [i for i, l in enumerate(revealed) if l == "_"]
        if unrevealed:
            idx = random.choice(unrevealed)
            revealed[idx] = answer[idx]

        hint_display = " ".join(revealed)
        await interaction.response.send_message(
            f"💡 Hint (costs 1 point): {hint_display}\n"
            f"❤️ Points left: {game['points']}"
        )

    # ----- Listen for guesses in channel -----
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        game = self.games.get(message.guild.id)
        if not game:
            return

        guess_word = message.content.strip().upper()
        answer = game["word"]

        if len(guess_word) != len(answer):
            return

        # Wordle feedback
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

        if guess_word == answer:
            points_won = game["points"]
            del self.games[message.guild.id]
            await message.channel.send(
                f"🎉 **Correct!** The word was **{answer}**\n{feedback_line}\n"
                f"🏆 You earned **{points_won} points!**"
            )
        elif game["guesses"] <= 0:
            points_lost = game["points"]
            del self.games[message.guild.id]
            await message.channel.send(
                f"💀 Out of guesses! The word was **{answer}**\n{feedback_line}\n"
                f"⚠ You lost **{points_lost} points**"
            )
        else:
            await message.channel.send(
                f"{feedback_line}\n💡 Hint: {game['hint']}\n"
                f"❤️ Guesses left: {game['guesses']} | Points: {game['points']}"
            )

        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Game(bot))