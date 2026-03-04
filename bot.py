import discord
from discord.ext import commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # needed for guessing via chat

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Load game cog
        await self.load_extension("cogs.game")

        # Sync slash commands globally
        await self.tree.sync()
        print("Commands synced")

bot = Bot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)