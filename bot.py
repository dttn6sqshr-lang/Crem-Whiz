import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN environment variable not set")

intents = discord.Intents.default()

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