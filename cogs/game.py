import discord
from discord.ext import commands
import random
import json
import os

# load words
with open("data/words.json", "r") as f:
    WORD_BANK = json.load(f)

# leaderboard
LEADERBOARD_FILE = "data/leaderboard.json"
if os.path.exists(LEADERBOARD_FILE):
    with open(LEADERBOARD_FILE, "r") as f:
        LEADERBOARD = json.load(f)
else:
    LEADERBOARD = {}

active_games = {}

def choose_word(category):
    word_entry = random.choice(WORD_BANK[category])
    return word_entry["word"].upper(), word_entry["hint"], word_entry["difficulty"]

def wordle_feedback(word, guess):
    feedback = ""
    word_letters = list(word)
    guess_letters = list(guess.upper())
    for i, letter in enumerate(guess_letters):
        if i < len(word_letters):
            if letter == word_letters[i]:
                feedback += "💚"
            elif letter in word_letters:
                feedback += "💛"
            else:
                feedback += "⬛"
        else:
            feedback += "⬛"
    return feedback

def save_leaderboard():
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(LEADERBOARD, f, indent=2)

class CrèmeWhiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="startgame", description="Start a Crème Whiz round")
    async def startgame(self, ctx):
        categories = list(WORD_BANK.keys())
        options = [discord.SelectOption(label=cat) for cat in categories]
        select = discord.ui.Select(placeholder="Select a category", options=options)

        async def dropdown_callback(interaction):
            user_id = str(interaction.user.id)
            word, hint, difficulty = choose_word(select.values[0])
            active_games[user_id] = {
                "word": word,
                "hint": hint,
                "category": select.values[0],
                "difficulty": difficulty,
                "guesses_left": 3,
                "streak": LEADERBOARD.get(user_id, {}).get("streak",0),
                "points": LEADERBOARD.get(user_id, {}).get("points",0),
                "hint_used": False
            }
            await interaction.response.send_message(
                f"🕵️ Category: {select.values[0]}\n"
                f"🎲 Difficulty: {difficulty}\n"
                f"📝 Word length: {len(word)} letters\n"
                f"Hint: {hint}\n"
                f"You have 3 guesses. Use `/guess [word]`!")
        select.callback = dropdown_callback
        view = discord.ui.View()
        view.add_item(select)
        await ctx.send("🎉 Crème Whiz – pick a category!", view=view)

    @discord.slash_command(name="guess", description="Submit a guess")
    async def guess(self, ctx, word: str):
        user_id = str(ctx.author.id)
        if user_id not in active_games:
            return await ctx.send("❌ No active game. Use `/startgame`")

        game = active_games[user_id]
        if game["guesses_left"] <= 0:
            await ctx.send(f"❌ Out of guesses! Word was {game['word']}")
            del active_games[user_id]
            return

        game["guesses_left"] -= 1
        feedback = wordle_feedback(game["word"], word)

        if word.upper() == game["word"]:
            pts_map = {3:50,2:70,1:100}
            base = pts_map[3 - game["guesses_left"]]
            if game["hint_used"]:
                base -= 20
            game["points"] += base
            game["streak"] += 1
            LEADERBOARD[user_id] = {"points":game["points"], "streak":game["streak"]}
            save_leaderboard()
            await ctx.send(f"✅ You guessed it! {game['word']}\nPoints:{base}\nStreak:{game['streak']}")
            del active_games[user_id]
            return

        if game["guesses_left"] == 0:
            await ctx.send(f"{feedback}\n❌ Out of guesses! Word was {game['word']}")
            del active_games[user_id]
        else:
            await ctx.send(f"{feedback}\nGuesses left: {game['guesses_left']}\nUse `/hint`")

    @discord.slash_command(name="hint", description="Reveal a hint (costs 20 points)")
    async def hint(self, ctx):
        user_id = str(ctx.author.id)
        if user_id not in active_games:
            return await ctx.send("❌ No active game")
        game = active_games[user_id]
        if game["hint_used"]:
            return await ctx.send("❌ Hint already used!")
        game["hint_used"] = True
        await ctx.send(f"💡 Extra hint: {game['hint']}")

    @discord.slash_command(name="stats", description="Show your Crème Whiz stats")
    async def stats(self, ctx):
        user_id = str(ctx.author.id)
        stats = LEADERBOARD.get(user_id, {"points":0,"streak":0})
        await ctx.send(f"📊 Points: {stats['points']}\nStreak: {stats['streak']}")

    @discord.slash_command(name="leaderboard", description="Show top players")
    async def leaderboard(self, ctx):
        sorted_lb = sorted(LEADERBOARD.items(), key=lambda x:x[1]["points"], reverse=True)[:10]
        desc=""
        for i,(u,d) in enumerate(sorted_lb,1):
            try:
                user = await self.bot.fetch_user(int(u))
                desc += f"{i}. {user.name} — {d['points']} pts (Streak {d['streak']})\n"
            except:
                desc += f"{i}. Unknown — {d['points']} pts\n"
        await ctx.send(f"🏆 Leaderboard:\n{desc}")