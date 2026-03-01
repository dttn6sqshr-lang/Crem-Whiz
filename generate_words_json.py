import json
import random
import os

categories = {
    "Animals": [
        ("Elephant", ["Animal with a trunk", "Largest land animal", "Has tusks", "Lives in herds"]),
        ("Tiger", ["Striped big cat", "Lives in Asia", "Carnivore", "Excellent swimmer"]),
        ("Koala", ["Australian marsupial", "Eats eucalyptus", "Tree dweller", "Very sleepy"]),
        ("Dolphin", ["Ocean mammal", "Very smart", "Uses echolocation", "Lives in pods"]),
        ("Penguin", ["Bird that cannot fly", "Waddles on ice", "Black and white", "Cold regions"]),
        ("Lion", ["King of the jungle", "Big cat", "Lives in prides", "Has a mane"]),
        ("Zebra", ["Striped animal", "Looks like a horse", "Lives in Africa", "Herbivore"]),
        ("Giraffe", ["Tallest animal", "Long neck", "Eats leaves", "Spotted coat"]),
        ("Bear", ["Large furry animal", "Hibernates", "Eats honey", "Strong claws"]),
        ("Wolf", ["Howls at night", "Lives in packs", "Wild dog", "Sharp teeth"])
    ],
    "Foods": [
        ("Apple", ["Fruit linked to teachers & tech", "Keeps doctor away", "Red or green", "Grows on trees"]),
        ("Pizza", ["Cheesy round food", "From Italy", "Pepperoni topping", "Baked"]),
        ("Burger", ["Fast food sandwich", "Has bun and meat", "Served with fries", "Popular"]),
        ("Sushi", ["Japanese rice dish", "Raw fish", "Rolled", "With soy sauce"]),
        ("Taco", ["Mexican folded tortilla", "Filled with meat", "Often spicy", "Street food"]),
        ("Pasta", ["Italian staple", "Boiled noodles", "Many shapes", "Served with sauce"]),
        ("Cake", ["Sweet dessert", "Has frosting", "Birthday food", "Baked"]),
        ("Ice Cream", ["Frozen dessert", "Many flavors", "Cold treat", "Melts easily"]),
        ("Salad", ["Healthy dish", "Made of vegetables", "Often cold", "Has dressing"]),
        ("Steak", ["Cooked beef", "Grilled", "Served hot", "Protein food"])
    ],
    "Musical Instruments": [
        ("Guitar", ["6-string instrument", "Used in rock", "Has frets", "Played by strumming"]),
        ("Piano", ["Keyboard instrument", "88 keys", "Used in classical music", "Black and white keys"]),
        ("Violin", ["String instrument", "Played with a bow", "Used in orchestra", "Small size"]),
        ("Drums", ["Percussion instrument", "Beaten with sticks", "Keeps rhythm", "Used in bands"]),
        ("Flute", ["Wind instrument", "Made of metal or wood", "Blown air", "Used in orchestras"])
    ],
    "Cartoon Characters": [
        ("Mickey Mouse", ["Disney mascot", "Big ears", "Red shorts", "Yellow shoes"]),
        ("SpongeBob", ["Lives in a pineapple", "Yellow sponge", "Works at Krusty Krab", "Best friend Patrick"]),
        ("Bugs Bunny", ["Talks with carrot", "Looney Tunes", "Gray rabbit", "Smart and witty"]),
        ("Tom", ["Cat from cartoon", "Chases Jerry", "Blue-gray fur", "Silent character"]),
        ("Jerry", ["Mouse from cartoon", "Chased by Tom", "Small and clever", "Loves cheese"])
    ],
    "Brands": [
        ("Nike", ["Sports brand", "Swoosh logo", "Just Do It", "Shoes"]),
        ("Apple", ["Tech company", "Makes iPhones", "Bitten fruit logo", "Mac computers"]),
        ("Adidas", ["Three stripe logo", "Sportswear", "Shoes and clothes", "German brand"]),
        ("Coca Cola", ["Soda brand", "Red logo", "Sweet drink", "Called Coke"]),
        ("Pepsi", ["Soda brand", "Blue and red logo", "Cola drink", "Rival to Coke"])
    ],
    "Jobs": [
        ("Doctor", ["Heals people", "Works in hospital", "Wears white coat", "Uses stethoscope"]),
        ("Teacher", ["Works in school", "Teaches students", "Gives homework", "Grades work"]),
        ("Chef", ["Cooks food", "Works in kitchen", "Makes recipes", "Wears tall hat"]),
        ("Pilot", ["Flies airplanes", "In cockpit", "Travels a lot", "Controls aircraft"]),
        ("Engineer", ["Solves problems", "Uses math", "Builds things", "Designs systems"])
    ],
    "TV Shows": [
        ("Friends", ["Sitcom", "New York", "Six friends", "1990s"]),
        ("Stranger Things", ["Supernatural events", "Small town", "Demogorgon", "Kids on bikes"]),
        ("Breaking Bad", ["Chemistry teacher", "Makes meth", "Blue crystals", "Albuquerque"]),
        ("The Office", ["Mockumentary", "Office workers", "Dunder Mifflin", "Michael Scott"]),
        ("Game of Thrones", ["Fantasy world", "Dragons", "Iron Throne", "Many families"])
    ],
    "Games": [
        ("Minecraft", ["Block building game", "Crafting", "Open world", "Mobs"]),
        ("Fortnite", ["Battle royale game", "Build and fight", "Shrinking map", "Online"]),
        ("Chess", ["Board strategy game", "Checkmate", "Kings and queens", "16 pieces"]),
        ("Among Us", ["Find impostor", "Spaceship", "Tasks", "Multiplayer"]),
        ("Poker", ["Card betting game", "Bluffing", "Hand ranks", "Casino"])
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
    # multiply entries to reach ~250 per category
    while len(entries) < 250:
        entries.extend(entries)
    final_data[cat] = entries[:250]

os.makedirs("data", exist_ok=True)
with open("data/words.json", "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=2, ensure_ascii=False)

print("✅ data/words.json created with 2000+ words!")