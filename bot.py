import os
import discord
from discord.ext import commands
from cogs.game import Game

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Load the game cog
bot.add_cog(Game(bot))

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user}')

# Use environment variable for the token
bot.run(os.getenv("DISCORD_TOKEN"))