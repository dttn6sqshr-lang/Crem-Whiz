import discord
from discord.ext import commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")  # make sure your bot token is set in environment variables

intents = discord.Intents.default()
intents.message_content = True  # optional if you want to process normal messages later

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== Setup event =====
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    print("Syncing application commands...")
    await bot.tree.sync()  # sync slash commands globally
    print("Slash commands synced!")

# ===== Simple test slash command =====
@bot.tree.command(name="ping", description="Test command")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")

# ===== Load Game cog =====
async def load_game_cog():
    await bot.load_extension("cogs.game")  # adjust path if needed

bot.loop.create_task(load_game_cog())

# ===== Run bot =====
bot.run(TOKEN)