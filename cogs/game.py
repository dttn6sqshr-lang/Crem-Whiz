import discord
from discord.ext import commands
from discord import app_commands
import json
import random

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

        with open("data/words.json", "r", encoding="utf-8") as f:
            self.words = json.load(f)

    # ---------- CATEGORY SELECT ----------
    class CategorySelect(discord.ui.Select):
        def __init__(self, categories, parent):
            self.parent = parent
            options = [
                discord.SelectOption(label=cat, description=f"Play {cat}")
                for cat in categories
            ]
            super().__init__(
                placeholder="Choose a category...",
                min_values=1,
                max_values=1,
                options=options
            )

        async def callback(self, interaction: discord.Interaction):
            category = self.values[0]
            entry = random.choice(self.parent.words[category])

            self.parent.games[interaction.guild_id] = {
                "word": entry["word"].upper(),
                "hint": entry["hint"],
                "guesses": 3
            }

            await interaction.response.send_message(
                f"🍦 **Crème Whiz Started!**\n"
                f"📚 Category: **{category}**\n"
                f"💡 Hint: {entry['hint']}\n"
                f"❤️ Guesses: **3**\n\n"
                f"Use **/guess <word>**",
                ephemeral=False
            )

    class CategoryView(discord.ui.View):
        def __init__(self, categories, parent):
            super().__init__()
            self.add_item(Game.CategorySelect(categories, parent))

    # ---------- START GAME ----------
    @app_commands.command(name="startgame", description="Start a Crème Whiz game")
    async def startgame(self, interaction: discord.Interaction):
        view = Game.CategoryView(self.words.keys(), self)
        await interaction.response.send_message(
            "🍨 Choose a category:",
            view=view,
            ephemeral=True
        )

    # ---------- GUESS ----------
    @app_commands.command(name="guess", description="Guess the word")
    @app_commands.describe(word="Your guess")
    async def guess(self, interaction: discord.Interaction, word: str):
        game = self.games.get(interaction.guild_id)

        if not game:
            await interaction.response.send_message(
                "❌ No game running. Use **/startgame** first.",
                ephemeral=True
            )
            return

        word = word.upper()
        answer = game["word"]

        if word == answer:
            del self.games[interaction.guild_id]
            await interaction.response.send_message(
                f"🎉 Correct! The word was **{answer}**"
            )
        else:
            game["guesses"] -= 1

            if game["guesses"] <= 0:
                del self.games[interaction.guild_id]
                await interaction.response.send_message(
                    f"💀 Out of guesses! The word was **{answer}**"
                )
            else:
                await interaction.response.send_message(
                    f"❌ Wrong guess!\n"
                    f"💡 Hint: {game['hint']}\n"
                    f"❤️ Guesses left: {game['guesses']}"
                )

async def setup(bot):
    await bot.add_cog(Game(bot))