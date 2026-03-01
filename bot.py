import discord
from discord.ext import commands

TOKEN = "PUT_YOUR_TOKEN_HERE"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

async def load():
    await bot.load_extension("cogs.game")

bot.loop.create_task(load())

bot.run(TOKEN)