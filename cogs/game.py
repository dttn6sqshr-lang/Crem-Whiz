import discord
from discord.ext import commands
from discord import app_commands
import json
import random

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

        with open("data/words.json", "r") as f:
            self.words = json.load(f)

    class CategorySelect(discord.ui.Select):
        def __init__(self, categories, cog):
            self.cog = cog
            options = [discord.SelectOption(label=c) for c in categories]
            super().__init__(placeholder="Choose category", options=options)

        async def callback(self, interaction: discord.Interaction):
            category = self.values[0]
            entry = random.choice(self.cog.words[category])

            self.cog.games[interaction.guild_id] = {
                "word": entry["word"],
                "hint": entry["hint"],
                "guesses": 3
            }

            await interaction.response.send_message(
                f"🎮 Game started!\n"
                f"📚 Category: {category}\n"
                f"💡 Hint: {entry['hint']}\n"
                f"❤️ Guesses: 3\n"
                f"Use `/guess <word>`"
            )

    class CategoryView(discord.ui.View):
        def __init__(self, categories, cog):
            super().__init__()
            self.add_item(Game.CategorySelect(categories, cog))

    @app_commands.command(name="startgame", description="Start a game")
    async def startgame(self, interaction: discord.Interaction):
        view = Game.CategoryView(self.words.keys(), self)
        await interaction.response.send_message("Choose a category:", view=view)

    @app_commands.command(name="guess", description="Guess the word")
    async def guess(self, interaction: discord.Interaction, word: str):
        game = self.games.get(interaction.guild_id)

        if not game:
            await interaction.response.send_message("❌ No game running. Use /startgame")
            return

        word = word.upper()
        if word == game["word"]:
            del self.games[interaction.guild_id]
            await interaction.response.send_message(f"🎉 Correct! Word was {word}")
        else:
            game["guesses"] -= 1
            if game["guesses"] <= 0:
                answer = game["word"]
                del self.games[interaction.guild_id]
                await interaction.response.send_message(f"💀 Out of guesses! Word was {answer}")
            else:
                await interaction.response.send_message(
                    f"❌ Wrong!\n"
                    f"💡 Hint: {game['hint']}\n"
                    f"❤️ Guesses left: {game['guesses']}"
                )

async def setup(bot):
    await bot.add_cog(Game(bot))