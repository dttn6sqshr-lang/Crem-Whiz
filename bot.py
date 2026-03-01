import discord
from discord.ext import commands
import os
import json
import random
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ GENERATE WORDS IF MISSING ------------------

def generate_words_json():
    if not os.path.exists("data"):
        os.makedirs("data")
    if os.path.exists("data/words.json"):
        return  # already exists

    categories = {
        "Animals": [
            ("Elephant", ["Animal with a trunk", "Largest land animal", "Has tusks", "Lives in herds"]),
            ("Tiger", ["Striped big cat", "Lives in Asia", "Carnivore", "Excellent swimmer"]),
            ("Koala", ["Australian marsupial", "Eats eucalyptus", "Tree dweller", "Very sleepy"]),
            ("Dolphin", ["Ocean mammal", "Very smart", "Uses echolocation", "Lives in pods"]),
            ("Penguin", ["Bird that cannot fly", "Waddles on ice", "Black and white", "Cold regions"])
        ],
        "Foods": [
            ("Apple", ["Fruit linked to teachers & tech", "Keeps doctor away", "Red or green", "Grows on trees"]),
            ("Pizza", ["Cheesy round food", "From Italy", "Pepperoni topping", "Baked"]),
            ("Burger", ["Fast food sandwich", "Has bun and meat", "Served with fries", "Popular"]),
            ("Sushi", ["Japanese rice dish", "Raw fish", "Rolled", "With soy sauce"]),
            ("Taco", ["Mexican folded tortilla", "Filled with meat", "Often spicy", "Street food"])
        ]
    }

    # Build "All" category
    categories["All"] = []
    for cat in categories:
        if cat != "All":
            categories["All"].extend(categories[cat])

    final_data = {}
    for cat, words in categories.items():
        entries = []
        for word, hints in words:
            entries.append({
                "word": word.upper(),
                "start_hint": hints[0],
                "hint1": hints[1],
                "hint2": hints[2],
                "hint3": hints[3],
                "difficulty": random.randint(1, 6)
            })
        # multiply list to reach 250 per category
        while len(entries) < 250:
            entries.extend(entries)
        final_data[cat] = entries[:250]

    with open("data/words.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    print("✅ data/words.json created!")

# Generate words if missing
generate_words_json()

# ------------------ LOAD WORDS ------------------

with open("data/words.json", "r", encoding="utf-8") as f:
    WORDS = json.load(f)

# ------------------ BOT SETUP ------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(e)

async def main():
    async with bot:
        # if you have a cog, load it here
        # await bot.load_extension("cogs.game")
        await bot.start(TOKEN)

asyncio.run(main())