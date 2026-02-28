import discord
from discord.ext import commands
from cogs.game import CrèmeWhiz

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

bot.add_cog(CrèmeWhiz(bot))

@bot.event
async def on_ready():
    print(f"✅ Crème Whiz bot online as {bot.user}")

bot.run("YOUR_BOT_TOKEN")