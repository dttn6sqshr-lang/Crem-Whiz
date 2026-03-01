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
        self.scores = {}  # {guild_id: {user_id: points}}

        # Load words
        with open("data/words.json", "r", encoding="utf-8") as f:
            self.words = json.load(f)

        # Hidden difficulties (points per word)
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
            await self.cog.start_round(interaction, category, interaction.user)

    class CategoryView(discord.ui.View):
        def __init__(self, categories, cog):
            super().__init__()
            self.add_item(Game.CategorySelect(categories, cog))

    # ----- /startgame -----
    @app_commands.command(name="startgame", description="Start a Crème Whiz game")
    async def startgame(self, interaction: discord.Interaction):
        view = Game.CategoryView(self.words.keys(), self)
        await interaction.response.send_message("Choose a category:", view=view)

    # ----- /hint command -----
    @app_commands.command(name="hint", description="Use a hint (costs 1 point)")
    async def hint(self, interaction: discord.Interaction):
        game = self.games.get(interaction.guild_id)
        if not game:
            await interaction.response.send_message(
                "❌ No game running. Use /startgame first.", ephemeral=True
            )
            return

        user_id = interaction.user.id
        guild_scores = self.scores.setdefault(interaction.guild_id, {})
        guild_scores[user_id] = guild_scores.get(user_id, 0)
        if guild_scores[user_id] > 0:
            guild_scores[user_id] -= 1

        answer = game["word"]
        revealed = ["_" for _ in answer]
        revealed[0] = answer[0]
        unrevealed = [i for i, l in enumerate(revealed) if l == "_"]
        if unrevealed:
            idx = random.choice(unrevealed)
            revealed[idx] = answer[idx]

        hint_display = " ".join(revealed)
        await interaction.response.send_message(
            f"💡 Hint (costs 1 point): {hint_display}\n"
            f"🏆 {interaction.user.display_name}, your total points: {guild_scores[user_id]}"
        )

    # ----- /score command -----
    @app_commands.command(name="score", description="Check your total points")
    async def score(self, interaction: discord.Interaction):
        guild_scores = self.scores.get(interaction.guild_id, {})
        points = guild_scores.get(interaction.user.id, 0)
        await interaction.response.send_message(
            f"🏆 {interaction.user.display_name}, you have **{points} points**!"
        )

    # ----- /leaderboard command -----
    @app_commands.command(name="leaderboard", description="Show top 10 players in this server")
    async def leaderboard(self, interaction: discord.Interaction):
        guild_scores = self.scores.get(interaction.guild_id, {})
        if not guild_scores:
            await interaction.response.send_message("No points yet! Start playing with /startgame.")
            return

        top = sorted(guild_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        embed = discord.Embed(title="🏆 Crème Whiz Leaderboard", color=discord.Color.gold())
        for rank, (user_id, points) in enumerate(top, start=1):
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            embed.add_field(name=f"{rank}. {name}", value=f"{points} points", inline=False)
        await interaction.response.send_message(embed=embed)

    # ----- Start a round -----
    async def start_round(self, interaction, category, user):
        await self.start_next_word(interaction.channel, category, user, first=True)

    # ----- Handle guesses -----
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = message.guild.id
        game = self.games.get(guild_id)
        if not game:
            return

        guess_word = message.content.strip().upper()
        answer = game["word"]
        if len(guess_word) != len(answer):
            return

        # Wordle-style feedback
        feedback = []
        answer_letters = list(answer)
        for i in range(len(guess_word)):
            if guess_word[i] == answer[i]:
                feedback.append("🟩")
                answer_letters[i] = None
            else:
                feedback.append(None)
        for i in range(len(guess_word)):
            if feedback[i] is None:
                if guess_word[i] in answer_letters:
                    feedback[i] = "🟨"
                    answer_letters[answer_letters.index(guess_word[i])] = None
                else:
                    feedback[i] = "⬛"
        feedback_line = "".join(feedback)

        first_try = game["guesses"] == 3
        correct = guess_word == answer
        guild_scores = self.scores.setdefault(guild_id, {})

        if correct:
            user = game["user"]
            guild_scores[user.id] = guild_scores.get(user.id, 0) + game["points"]
            await message.channel.send(
                f"🎉 **Correct!** The word was **{answer}**\n"
                f"🏆 You earned **{game['points']} points!**\n"
                f"💰 Total points: {guild_scores[user.id]}"
            )
            await self.start_next_word(message.channel, game["category"], user)
        else:
            # Deduct guess only if not first attempt
            game["guesses"] -= 1 if not first_try else 0
            await message.channel.send(
                f"{feedback_line}\n❤️ Guesses left: {game['guesses']}"
            )
            if game["guesses"] <= 0:
                await message.channel.send(
                    f"💀 Out of guesses! The word was **{answer}**\n"
                    f"⚠ You earned 0 points. Use /startgame to start a new category."
                )
                await self.end_game_cleanup(guild_id)

        await self.bot.process_commands(message)

    # ----- Start next word -----
    async def start_next_word(self, channel, category, user, first=False):
        entry = random.choice(self.words[category])
        difficulty = random.choice(self.difficulties)
        guild_id = channel.guild.id

        # Cancel previous timer if exists
        prev_task = self.games.get(guild_id, {}).get("timer_task")
        if prev_task:
            prev_task.cancel()

        # Initialize new word game
        self.games[guild_id] = {
            "word": entry["word"].upper(),
            "hint": entry["hint"],
            "guesses": 3,
            "points": difficulty["points"],
            "user": user,
            "category": category,
            "timer_alerts_sent": {"30": False, "15": False}
        }

        # Start per-round timer
        task = self.bot.loop.create_task(self.timer_with_alerts(channel, guild_id))
        self.games[guild_id]["timer_task"] = task

        word_len = len(entry["word"])
        msg = f"📚 Category: **{category}** | ✏ Word length: {word_len} letters\n" \
              f"💡 Hint: {entry['hint']} | ❤️ Guesses: 3 | Points: {difficulty['points']}"
        if first:
            msg = "🎮 **Crème Whiz Started!**\n" + msg + "\nType your guess in the channel! Use `/hint`."
        else:
            msg = "🎮 **Next word!**\n" + msg + "\nType your guess in the channel!"

        await channel.send(msg)

    # ----- Timer per round with alerts -----
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

            # Time's up
            game = self.games.get(guild_id)
            if game:
                answer = game["word"]
                await channel.send(
                    f"⏰ Time's up! The word was **{answer}**\n"
                    f"⚠ You earned 0 points. Use /startgame to start a new category."
                )
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