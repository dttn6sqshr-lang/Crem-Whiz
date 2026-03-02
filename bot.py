import discord
from discord.ext import commands
from cogs.game import Game

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Register the Cog
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

bot.add_cog(Game(bot))

bot.run("YOUR_BOT_TOKEN")  # Keep this in env variables!