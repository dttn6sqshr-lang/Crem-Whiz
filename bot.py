import discord
from discord.ext import commands
import os

# Intents
intents = discord.Intents.default()
intents.message_content = True  # Needed to read guesses typed in channel

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# Load cogs on startup
@bot.event
async def setup_hook():
    await bot.load_extension("cogs.game")  # Your cog path

# Ready event
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Run the bot using token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")  # Set your Railway/GitHub secret as DISCORD_TOKEN
bot.run(TOKEN)