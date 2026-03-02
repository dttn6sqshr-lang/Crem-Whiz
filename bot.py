import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Bot is online and ready!")

# Load cogs
bot.load_extension("cogs.game")

bot.run(os.getenv("DISCORD_TOKEN"))