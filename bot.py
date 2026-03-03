import discord
from discord import app_commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")

class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("Synced")

bot = Bot()

@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")

bot.run(TOKEN)