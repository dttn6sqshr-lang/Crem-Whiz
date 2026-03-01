import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable not set!")

# ⚡ Enable all necessary intents
intents = discord.Intents.default()
intents.message_content = True  # required for reading messages typed by users
intents.guilds = True  # required for slash commands
intents.messages = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.load_extension("cogs.game")
        await self.tree.sync()
        print("✅ Commands synced")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)