import discord
from discord.ext import commands

TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} is online and commands synced")

async def load_cogs():
    await bot.load_extension("cogs.game")

bot.loop.create_task(load_cogs())

bot.run(TOKEN)