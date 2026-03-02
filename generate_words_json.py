import json
import os
import random

# ✅ Folder where your .txt files live
DATA_FOLDER = "data"

# Ensure the data folder exists
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)
    print(f"Created missing folder: {DATA_FOLDER}")

# Output JSON file
OUTPUT_FILE = os.path.join(DATA_FOLDER, "words.json")

# Your category files
CATEGORY_FILES = {
    "All": "all.txt",
    "Animals": "animals.txt",
    "Foods": "foods.txt",
    "Hobbies": "hobbies.txt",
    "Jobs": "job.txt",
    "Characters": "characters.txt"
}

def read_words(file_path):
    """Read words from a file, remove empty lines and duplicates."""
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found, skipping this category.")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        words = f.read().splitlines()
    return list(set([w.strip() for w in words if w.strip()]))

def generate_hints(word, category):
    """Generate a start hint + 3 progressive hints depending on category."""
    word_upper = word.upper()
    length = len(word_upper)
    first = word_upper[0]

    if category == "Animals":
        start_hint = "An animal"
        hint1 = f"{length} letters"
        hint2 = "It is a living creature"
        hint3 = f"Starts with '{first}'"
    elif category == "Foods":
        start_hint = "A type of food"
        hint1 = f"{length} letters"
        hint2 = "People eat this"
        hint3 = f"Starts with '{first}'"
    elif category == "Hobbies":
        start_hint = "A hobby or activity"
        hint1 = f"{length} letters"
        hint2 = "People do this for fun"
        hint3 = f"Starts with '{first}'"
    elif category == "Jobs":
        start_hint = "A job or profession"
        hint1 = f"{length} letters"
        hint2 = "Someone works as this"
        hint3 = f"Starts with '{first}'"
    elif category == "Characters":
        start_hint = "A fictional or real character"
        hint1 = f"{length} letters"
        hint2 = "Appears in movies, books, or shows"
        hint3 = f"Starts with '{first}'"
    else:
        start_hint = "A word"
        hint1 = f"{length} letters"
        hint2 = f"Starts with '{first}'"
        hint3 = f"Ends with '{word_upper[-1]}'"

    return start_hint, hint1, hint2, hint3

output = {}

for category, filename in CATEGORY_FILES.items():
    path = os.path.join(DATA_FOLDER, filename)
    words = read_words(path)
    output[category] = []

    for word in words:
        start_hint, hint1, hint2, hint3 = generate_hints(word, category)
        difficulty = random.randint(1, 4)  # 1=easy, 4=hard

        entry = {
            "word": word.upper(),
            "start_hint": start_hint,
            "hint1": hint1,
            "hint2": hint2,
            "hint3": hint3,
            "difficulty": difficulty
        }

        output[category].append(entry)

print(f"Processed categories: {list(CATEGORY_FILES.keys())}")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"words.json successfully generated at: {OUTPUT_FILE}")
print(f"Total words: {sum(len(v) for v in output.values())}")