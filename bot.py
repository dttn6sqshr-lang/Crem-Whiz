import os
import discord
from discord.ext import commands
from cogs.game import Game

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()  # Sync slash commands
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(e)

async def main():
    # Await the add_cog coroutine
    await bot.add_cog(Game(bot))
    await bot.start(os.getenv("DISCORD_TOKEN"))

# Run the bot
import asyncio
asyncio.run(main())