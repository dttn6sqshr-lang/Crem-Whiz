import discord
from discord.ext import commands
from discord import app_commands
import json
import random

TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

games = {}  # {guild_id: game_data}

# Load words
with open("data/words.json", "r", encoding="utf-8") as f:
    WORDS = json.load(f)

# ---------- READY ----------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} is online & commands synced")

# ---------- CATEGORY MENU ----------
class CategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cat, description=f"Play category: {cat}")
            for cat in WORDS.keys()
        ]
        super().__init__(
            placeholder="Choose a category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        entry = random.choice(WORDS[category])

        games[interaction.guild_id] = {
            "word": entry["word"],
            "hint": entry["hint"],
            "guesses": 3
        }

        await interaction.response.send_message(
            f"🍦 **Crème Whiz Started!**\n"
            f"📚 Category: **{category}**\n"
            f"💡 Hint: {entry['hint']}\n"
            f"🎯 You have **3 guesses**!\n\n"
            f"Use **/guess <word>**"
        )

class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CategorySelect())

# ---------- START GAME ----------
@bot.tree.command(name="startgame", description="Start a Crème Whiz game")
async def startgame(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🍨 Pick a category to start:",
        view=CategoryView(),
        ephemeral=True
    )

# ---------- GUESS ----------
@bot.tree.command(name="guess", description="Guess the word")
@app_commands.describe(word="Your guess")
async def guess(interaction: discord.Interation, word: str):
    game = games.get(interaction.guild_id)

    if not game:
        await interaction.response.send_message(
            "❌ No game running. Use **/startgame** first.",
            ephemeral=True
        )
        return

    word = word.upper()
    answer = game["word"]

    if word == answer:
        del games[interaction.guild_id]
        await interaction.response.send_message(
            f"🎉 **Correct!** The word was **{answer}**"
        )
    else:
        game["guesses"] -= 1
        if game["guesses"] <= 0:
            del games[interaction.guild_id]
            await interaction.response.send_message(
                f"💀 Out of guesses! The word was **{answer}**"
            )
        else:
            await interaction.response.send_message(
                f"❌ Wrong guess!\n"
                f"💡 Hint: {game['hint']}\n"
                f"❤️ Guesses left: {game['guesses']}"
            )

# ---------- RUN ----------
bot.run(TOKEN)