import discord
from discord.ext import commands

TOKEN = "PUT_YOUR_TOKEN_HERE"

intents = discord.Intents.default()

class MyBot(commands.Bot):
    async def setup_hook(self):
        # Load cogs properly
        await self.load_extension("cogs.game")
        # Sync commands
        await self.tree.sync()
        print("✅ Commands synced")

bot = MyBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)