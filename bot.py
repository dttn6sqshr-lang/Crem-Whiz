# bot.py
import os
import discord
from discord.ext import commands
from cogs.game import Game  # your game cog

# Load token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

# Intents setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

# Create bot instance with slash command support
bot = commands.Bot(command_prefix="!", intents=intents)

# When bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        # Sync slash commands globally
        await bot.tree.sync()
        print("Slash commands synced!")
    except Exception as e:
        print("Error syncing slash commands:", e)

# Add your Game cog
bot.add_cog(Game(bot))

# Run the bot
bot.run(TOKEN)