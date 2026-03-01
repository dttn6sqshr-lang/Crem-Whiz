import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import asyncio

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}   # {guild_id: game_data}
        self.scores = {}  # {guild_id: {user_id: total_points}}

        # Load words
        with open("data/words.json", "r", encoding="utf-8") as f:
            self.words = json.load(f)

        # Hidden difficulties for points per word
        self.difficulties = [
            {"points": 1},  # Very Easy
            {"points": 2},  # Easy
            {"points": 3},  # Medium
            {"points": 4},  # Hard
            {"points": 5},  # Very Hard
            {"points": 6},  # Extreme
        ]

    # ----- Category dropdown -----
    class CategorySelect(discord.ui.Select):
        def __init__(self, categories, cog):
            self.cog = cog
            options = [discord.SelectOption(label=c, description=f"Play {c}") for c in categories]
            super().__init__(placeholder="Choose a category...", options=options)

        async def callback(self, interaction: discord.Interaction):
            category = self.values[0]
            await self.cog.start_round(interaction, category)

    class CategoryView(discord.ui.View):
        def __init__(self, categories, cog):
            super().__init__()
            self.add_item(Game.CategorySelect(categories, cog))

    # ----- /startgame -----
    @app_commands.command(name="startgame", description="Start a Crème Whiz game")
    async def startgame(self, interaction: discord.Interaction):
        view = Game.CategoryView(self.words.keys(), self)
        await interaction.response.send_message("Choose a category:", view=view)

    # ----- /stopgame -----
    @app_commands.command(name="stopgame", description="Stop the current game in this server")
    async def stopgame(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        game = self.games.pop(guild_id, None)
        if game:
            timer_task = game.get("timer_task")
            if timer_task:
                timer_task.cancel()
            await interaction.response.send_message("🛑 The current Crème Whiz game has been stopped.")
        else:
            await interaction.response.send_message("❌ No game is running in this server.", ephemeral=True)

    # ----- /hint command -----
    @app_commands.command(name="hint", description="Use a hint (max 3 per round, costs points)")
    async def hint(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        user_id = interaction.user.id
        game = self.games.get(guild_id)
        if not game:
            await interaction.response.send_message("❌ No game running. Use /startgame first.", ephemeral=True)
            return

        player = game["players"].setdefault(user_id, {"guesses_left": 3, "hints_used": 0, "name": interaction.user.name})
        if player["hints_used"] >= 3:
            await interaction.response.send_message("❌ You have used all 3 hints for this round.", ephemeral=True)
            return

        self.scores.setdefault(guild_id, {})
        self.scores[guild_id][user_id] = self.scores[guild_id].get(user_id, 0)
        deduction = player["hints_used"] + 1
        self.scores[guild_id][user_id] = max(0, self.scores[guild_id][user_id] - deduction)
        player["hints_used"] += 1

        # Reveal first letter + random letter
        answer = game["word"]
        revealed = ["_" for _ in answer]
        revealed[0] = answer[0]
        unrevealed = [i for i, l in enumerate(revealed) if l == "_"]
        if unrevealed:
            idx = random.choice(unrevealed)
            revealed[idx] = answer[idx]
        hint_display = " ".join(revealed)

        await interaction.response.send_message(
            f"💡 Hint ({player['hints_used']}/3, -{deduction} points): {hint_display}\n"
            f"🏆 {interaction.user.mention}, total points: {self.scores[guild_id][user_id]}"
        )

    # ----- /score command -----
    @app_commands.command(name="score", description="Check a player's total points")
    @app_commands.describe(user="Optional: Tag a user to see their points")
    async def score(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        guild_scores = self.scores.get(interaction.guild.id, {})
        points = guild_scores.get(user.id, 0)
        await interaction.response.send_message(f"🏆 {user.mention} has **{points} points**!")

    # ----- /leaderboard command -----
    @app_commands.command(name="leaderboard", description="Show top 10 players in this server")
    async def leaderboard(self, interaction: discord.Interaction):
        guild_scores = self.scores.get(interaction.guild.id, {})
        if not guild_scores:
            await interaction.response.send_message("No points yet! Start playing with /startgame.")
            return
        top = sorted(guild_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        embed = discord.Embed(title="🏆 Crème Whiz Leaderboard", color=discord.Color.gold())
        for rank, (user_id, points) in enumerate(top, start=1):
            member = interaction.guild.get_member(user_id)
            name = member.name if member else "Unknown"
            embed.add_field(name=f"{rank}. {name}", value=f"{points} points", inline=False)
        await interaction.response.send_message(embed=embed)

    # ----- Start round -----
    async def start_round(self, interaction, category):
        await self.start_next_word(interaction.channel, category)

    async def start_next_word(self, channel, category):
        entry = random.choice(self.words[category])
        difficulty = random.choice(self.difficulties)
        guild_id = channel.guild.id

        # Cancel previous timer if exists
        prev_task = self.games.get(guild_id, {}).get("timer_task")
        if prev_task:
            prev_task.cancel()

        # Initialize game
        self.games[guild_id] = {
            "word": entry["word"].upper(),
            "hint": entry["hint"],
            "category": category,
            "players": {},  # player_id: {guesses_left, hints_used, name}
            "points_per_word": difficulty["points"],
            "timer_alerts_sent": {"30": False, "15": False}
        }

        # Start timer safely
        task = asyncio.create_task(self.timer_with_alerts(channel, guild_id))
        self.games[guild_id]["timer_task"] = task

        await channel.send(
            f"🎮 **Next word!**\n📚 Category: **{category}** | ✏ Word length: {len(entry['word'])} letters\n"
            f"💡 Hint: {entry['hint']} | ❤️ Each player has 3 guesses | 🏆 Points per word: {difficulty['points']}\n"
            f"Type your guesses in the channel! Use `/hint` (max 3 hints per player)."
        )

    # ----- Handle guesses -----
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        game = self.games.get(guild_id)
        if not game:
            return

        guess = message.content.strip().upper()
        answer = game["word"]
        if len(guess) != len(answer):
            return

        user_id = message.author.id
        player = game["players"].setdefault(user_id, {"guesses_left": 3, "hints_used": 0, "name": message.author.name})
        if player["guesses_left"] <= 0:
            return

        # Wordle-style feedback
        feedback = []
        answer_letters = list(answer)
        for i in range(len(guess)):
            if guess[i] == answer[i]:
                feedback.append("🟩")
                answer_letters[i] = None
            else:
                feedback.append(None)
        for i in range(len(guess)):
            if feedback[i] is None:
                if guess[i] in answer_letters:
                    feedback[i] = "🟨"
                    answer_letters[answer_letters.index(guess[i])] = None
                else:
                    feedback[i] = "⬛"
        feedback_line = "".join(feedback)

        correct = guess == answer

        # Initialize guild scores
        self.scores.setdefault(guild_id, {})
        self.scores[guild_id][user_id] = self.scores[guild_id].get(user_id, 0)

        if correct:
            # Award points
            self.scores[guild_id][user_id] += game["points_per_word"]
            # Cancel timer since round ends immediately
            timer_task = game.get("timer_task")
            if timer_task:
                timer_task.cancel()
            await message.channel.send(
                f"✅ {message.author.mention} guessed correctly! +{game['points_per_word']} points\n"
                f"💰 Total points: {self.scores[guild_id][user_id]}"
            )

            # Mini scoreboard (names only)
            round_scores = []
            for pid, pdata in game["players"].items():
                total = self.scores[guild_id].get(pid, 0)
                name = pdata.get("name", "Unknown")
                round_scores.append(f"{name} - {total} points")
            scoreboard = "\n".join(round_scores)
            await message.channel.send(f"📊 **Current Scores (All Players):**\n{scoreboard}")

            # Move to next word automatically
            await asyncio.sleep(2)  # small delay before next word
            await self.start_next_word(message.channel, game["category"])
            return

        else:
            player["guesses_left"] -= 1
            await message.channel.send(f"{feedback_line}\n❤️ {message.author.name} guesses left: {player['guesses_left']}")

        await self.bot.process_commands(message)

    # ----- Timer per round -----
    async def timer_with_alerts(self, channel, guild_id):
        try:
            total_time = 90
            while total_time > 0:
                await asyncio.sleep(1)
                total_time -= 1
                game = self.games.get(guild_id)
                if not game:
                    return
                alerts = game["timer_alerts_sent"]
                if total_time == 30 and not alerts["30"]:
                    await channel.send("⏳ 30 seconds remaining!")
                    alerts["30"] = True
                if total_time == 15 and not alerts["15"]:
                    await channel.send("⏳ 15 seconds remaining!")
                    alerts["15"] = True

            # Timer ended, no one guessed correctly
            game = self.games.get(guild_id)
            if game:
                answer = game["word"]
                await channel.send(f"⏰ Time's up! The word was **{answer}**\nUse /startgame for the next word.")
                await self.end_game_cleanup(guild_id)
        except asyncio.CancelledError:
            return

    # ----- Cleanup -----
    async def end_game_cleanup(self, guild_id):
        game = self.games.pop(guild_id, None)
        if game:
            timer_task = game.get("timer_task")
            if timer_task:
                timer_task.cancel()

# ----- Cog setup -----
async def setup(bot: commands.Bot):
    await bot.add_cog(Game(bot))