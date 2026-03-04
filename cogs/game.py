import discord
from discord.ext import commands
from discord import app_commands
import json, random, os, asyncio, re

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/words.json")

def normalize(text):
    return re.sub(r"[^a-zA-Z]", "", text).upper()

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Track games per channel
        self.games = {}  # channel_id -> game state
        self.words = self.load_words()

    def load_words(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_words = []
        for cat in data.values():
            all_words.extend(cat)
        return all_words

    def pick_word(self, recent_words):
        choices = [w for w in self.words if w["word"] not in recent_words]
        if not choices:
            recent_words.clear()
            choices = self.words
        word = random.choice(choices)
        recent_words.append(word["word"])
        if len(recent_words) > 3:
            recent_words.pop(0)
        return word

    # ================= START =================
    @app_commands.command(name="gamestart", description="Start a new Guess the Word game")
    async def gamestart(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel_id = interaction.channel.id

        if channel_id in self.games and self.games[channel_id]["running"]:
            await interaction.followup.send("A game is already running in this channel.", ephemeral=True)
            return

        recent_words = self.games.get(channel_id, {}).get("recent_words", [])

        word_entry = self.pick_word(recent_words)
        word = word_entry["word"]

        state = {
            "running": True,
            "starter": interaction.user,
            "word": word,
            "word_entry": word_entry,
            "word_display": ["⬜"] * len(word),
            "timer": 60,
            "hearts": 5,
            "used_hints": [],
            "round_scores": {},
            "recent_words": recent_words,
            "timer_task": None,
            "round_number": self.games.get(channel_id, {}).get("round_number", 0) + 1
        }

        self.games[channel_id] = state

        await self.send_embed(interaction.channel)
        # Start timer
        state["timer_task"] = asyncio.create_task(self.timer_loop(interaction.channel))

    # ================= STOP =================
    @app_commands.command(name="stopgame", description="Stop the game")
    async def stopgame(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel_id = interaction.channel.id

        if channel_id not in self.games or not self.games[channel_id]["running"]:
            await interaction.followup.send("No game running.", ephemeral=True)
            return

        if interaction.user != self.games[channel_id]["starter"]:
            await interaction.followup.send("Only the starter can stop the game.", ephemeral=True)
            return

        await self.end_game(interaction.channel)

    # ================= LEADERBOARD =================
    @app_commands.command(name="leaderboard", description="Show global leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Aggregate total_scores across all channels
        total_scores = {}
        for state in self.games.values():
            for player, score in state.get("round_scores", {}).items():
                total_scores[player] = total_scores.get(player, 0) + score
        if not total_scores:
            await interaction.followup.send("No scores yet.", ephemeral=True)
            return
        lines = [f"◡◡  <:CC_trophy:1474577678790299821> {u} : {s} Points ♡  ࣪" for u, s in sorted(total_scores.items(), key=lambda x: x[1], reverse=True)]
        embed = discord.Embed(title="📊 Leaderboard", description="\n".join(lines), color=0x1b1c23)
        await interaction.followup.send(embed=embed)

    # ================= HINT =================
    @app_commands.command(name="hint", description="Get a hint for current word")
    async def hint(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel_id = interaction.channel.id
        if channel_id not in self.games or not self.games[channel_id]["running"]:
            await interaction.followup.send("No game running.", ephemeral=True)
            return

        state = self.games[channel_id]
        hints = [
            state["word_entry"].get("hint1"),
            state["word_entry"].get("hint2"),
            state["word_entry"].get("hint3")
        ]
        available = [h for h in hints if h and h not in state["used_hints"]]
        if not available:
            await interaction.followup.send("No more hints left.", ephemeral=True)
            return

        hint = available[0]
        state["used_hints"].append(hint)
        state["hearts"] = max(state["hearts"] - 1, 0)
        await self.send_embed(interaction.channel)
        await interaction.followup.send(f"💡 Hint: {hint}", ephemeral=True)

    # ================= TIMER LOOP =================
    async def timer_loop(self, channel):
        channel_id = channel.id
        state = self.games.get(channel_id)
        if not state:
            return
        try:
            while state["timer"] > 0 and state["running"]:
                await asyncio.sleep(1)
                state["timer"] -= 1
                if state["timer"] in (30, 15):
                    await channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {state['timer']} seconds remaining ⠀ּ ּ    ✧")
            if state["running"]:
                await self.end_game(channel)
        except asyncio.CancelledError:
            return

    # ================= MESSAGE LISTENER =================
    @commands.Cog.listener()
    async def on_message(self, message):
        channel_id = message.channel.id
        if message.author.bot:
            return
        if channel_id not in self.games:
            return
        state = self.games[channel_id]
        if not state["running"]:
            return
        if message.channel != message.channel:
            return

        guess = normalize(message.content)
        target = normalize(state["word"])
        valid_words = [normalize(w["word"]) for w in self.words]
        if guess not in valid_words:
            return

        # Wordle colors
        colors = []
        for i, c in enumerate(guess):
            if i < len(target):
                if c == target[i]:
                    colors.append("🟩")
                elif c in target:
                    colors.append("🟨")
                else:
                    colors.append("⬜")
            else:
                colors.append("⬜")
        await message.channel.send("".join(colors))

        player = message.author.name
        if guess == target:
            state["round_scores"][player] = state["round_scores"].get(player, 0) + 1
            state["hearts"] = 0
            await message.channel.send(f"🎉 {player} guessed the word! 🔥 Streak: {state.get('streaks', {}).get(player,0)+1}")
            await self.send_mini_leaderboard(message.channel)
            await self.end_game(message.channel)
        else:
            state["hearts"] -= 1
            state.setdefault("streaks", {})[player] = 0
            if state["hearts"] <= 0:
                await self.end_game(message.channel)
            else:
                await self.send_embed(message.channel)

    # ================= SEND EMBED =================
    async def send_embed(self, channel):
        state = self.games[channel.id]
        embed = discord.Embed(color=0x1b1c23)

        embed.add_field(
            name=f"﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚   |   ﹒🍥﹒ᣟᣟ୧ᣟᣟ {state['timer']}s ᣟᣟᣟ﹒♡﹒ᣟᣟ˚",
            value="",
            inline=False
        )
        streak_display = max(state.get("streaks", {}).values(), default=0)
        embed.add_field(
            name=f"♩  ﹒ ﹒  Streak  ﹒ ୨୧   |   ᣟ♩ᣟᣟ﹒ᣟ﹒ᣟ 🔥 {streak_display} ᣟ﹒ᣟ୨୧",
            value="",
            inline=False
        )
        embed.add_field(
            name="▪️▪️▪️▪️▪️",
            value="".join(state["word_display"]),
            inline=False
        )
        hearts_display = "❤️"*state["hearts"] + "🖤"*(5-state["hearts"])
        embed.add_field(name="⃕⠀⠀Timer 𓂃　۪ ׄ", value=hearts_display, inline=False)
        embed.add_field(name="⃕⠀⠀starter hint 𓂃　۪ ׄ", value=state["word_entry"].get("start_hint","No hint"), inline=False)
        embed.add_field(name="⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ", value="\n".join(state["used_hints"]) or "None", inline=False)

        await channel.send(embed=embed)

    # ================= MINI LEADERBOARD =================
    async def send_mini_leaderboard(self, channel):
        state = self.games[channel.id]
        lines = []
        sorted_scores = sorted(state["round_scores"].items(), key=lambda x: x[1], reverse=True)
        for player, score in sorted_scores:
            lines.append(f"◡◡  <:CC_trophy:1474577678790299821> {player} : {score} Points ♡  ࣪")
        embed = discord.Embed(title="Mini Leaderboard", description="\n".join(lines) or "No scores yet", color=0x1b1c23)
        await channel.send(embed=embed)

    # ================= END GAME =================
    async def end_game(self, channel):
        channel_id = channel.id
        state = self.games.get(channel_id)
        if not state:
            return
        # Cancel timer first
        if state.get("timer_task"):
            state["timer_task"].cancel()
            state["timer_task"] = None
        # Reset state immediately
        self.games[channel_id]["running"] = False

        embed = discord.Embed(
            title="˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ",
            description=f"The word was: **{state['word']}**\nUse `/gamestart` to play again",
            color=0x1b1c23
        )
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Game(bot))