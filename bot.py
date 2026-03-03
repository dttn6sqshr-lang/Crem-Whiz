import discord
from discord.ext import commands
from cogs.game import Game  # Make sure your cog is here
import os
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")

class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        # Load the game cog asynchronously
        await self.load_extension("cogs.game")
        await self.tree.sync()  # sync slash commands globally
        print("Cogs loaded and commands synced!")

bot = Bot()

@bot.tree.command(name="ping", description="Check if bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")

# Start the bot
bot.run(TOKEN)