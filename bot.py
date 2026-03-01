import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable not set!")

# ⚡ Enable message content intent
intents = discord.Intents.default()
intents.message_content = True  # <--- important

class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.game")
        await self.tree.sync()
        print("✅ Commands synced")

bot = MyBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)