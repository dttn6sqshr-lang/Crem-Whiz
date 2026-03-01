import discord
from discord.ext import commands
from discord import app_commands
import json
import random

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # {guild_id: game_data}

        with open("data/words.json", "r", encoding="utf-8") as f:
            self.words = json.load(f)

    # ----- Category dropdown -----
    class CategorySelect(discord.ui.Select):
        def __init__(self, categories, cog):
            self.cog = cog
            options = [discord.SelectOption(label=c, description=f"Play {c}") for c in categories]
            super().__init__(placeholder="Choose a category...", options=options)

        async def callback(self, interaction: discord.Interaction):
            category = self.values[0]
            entry = random.choice(self.cog.words[category])

            self.cog.games[interaction.guild_id] = {
                "word": entry["word"].upper(),
                "hint": entry["hint"],
                "guesses": 3,
                "points": 3  # Start with 3 points
            }

            word_len = len(entry["word"])
            await interaction.response.send_message(
                f"🎮 **Crème Whiz Started!**\n"
                f"📚 Category: **{category}**\n"
                f"✏ Word length: **{word_len} letters**\n"
                f"💡 Hint: {entry['hint']}\n"
                f"❤️ Guesses: 3 | Points: 3\n\n"
                f"Use `/guess <word>` to play or `/hint` for extra help!"
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

    # ----- /guess with Wordle feedback -----
    @app_commands.command(name="guess", description="Guess the word")
    @app_commands.describe(word="Your guess")
    async def guess(self, interaction: discord.Interaction, word: str):
        game = self.games.get(interaction.guild_id)
        if not game:
            await interaction.response.send_message(
                "❌ No game running. Use /startgame first.", ephemeral=True
            )
            return

        guess_word = word.upper()
        answer = game["word"]

        if len(guess_word) != len(answer):
            await interaction.response.send_message(
                f"⚠️ Your guess must be {len(answer)} letters long!", ephemeral=True
            )
            return

        feedback = []
        answer_letters = list(answer)

        # First pass: correct letters in correct positions
        for i in range(len(guess_word)):
            if guess_word[i] == answer[i]:
                feedback.append("🟩")
                answer_letters[i] = None
            else:
                feedback.append(None)

        # Second pass: correct letters in wrong positions
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
            del self.games[interaction.guild_id]
            await interaction.response.send_message(
                f"🎉 **Correct!** The word was **{answer}**\n{feedback_line}"
            )
        elif game["guesses"] <= 0:
            del self.games[interaction.guild_id]
            await interaction.response.send_message(
                f"💀 Out of guesses! The word was **{answer}**\n{feedback_line}"
            )
        else:
            await interaction.response.send_message(
                f"{feedback_line}\n💡 Hint: {game['hint']}\n"
                f"❤️ Guesses left: {game['guesses']} | Points: {game['points']}"
            )

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

        # Give a hint: reveal a random unrevealed letter position
        answer = game["word"]
        revealed = ["_" for _ in answer]
        for i, c in enumerate(answer):
            if i == 0:  # always reveal first letter
                revealed[i] = c

        # Randomly reveal another unrevealed letter if points > 0
        unrevealed_indices = [i for i, l in enumerate(revealed) if l == "_"]
        if unrevealed_indices:
            idx = random.choice(unrevealed_indices)
            revealed[idx] = answer[idx]

        hint_display = " ".join(revealed)
        await interaction.response.send_message(
            f"💡 Hint (costs 1 point): {hint_display}\n"
            f"❤️ Points left: {game['points']}"
        )

async def setup(bot):
    await bot.add_cog(Game(bot))