# bot.py
import os
import discord
from discord.ext import commands
from cogs.game import Game

# ======== Config ========
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

GUILD_ID = 123456789012345678  # replace with your server ID for instant slash command sync

# ======== Intents ========
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ======== On Ready ========
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        print("Slash commands synced to test guild!")
    except Exception as e:
        print("Error syncing slash commands:", e)

# ======== Add Cogs ========
bot.add_cog(Game(bot))

# ======== Run Bot ========
bot.run(TOKEN)