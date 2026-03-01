import discord
from discord.ext import commands
import os
import subprocess
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- RUN GENERATOR ----------------

def generate_words():
    print("🔄 Generating words.json...")
    subprocess.run(["python", "generate_words_json.py"], check=True)
    print("✅ words.json ready")

# ---------------- BOT EVENTS ------------------

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(e)

async def main():
    generate_words()  # <-- THIS runs your generator file
    async with bot:
        await bot.load_extension("cogs.game")
        await bot.start(TOKEN)

asyncio.run(main())