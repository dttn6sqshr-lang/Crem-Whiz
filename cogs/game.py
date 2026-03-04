import discord
from discord.ext import commands
from discord import app_commands
import json, random, os, asyncio, re
from datetime import datetime

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/words.json")

def normalize(text: str):
    return re.sub(r"[^a-zA-Z]", "", text).upper()

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_running = False
        self.channel = None
        self.starter = None

        self.word_entry = None
        self.word = ""
        self.word_display = []
        self.last_guess_colors = ""
        self.timer = 60
        self.timer_task = None
        self.round = 0

        self.used_hints = []
        self.round_scores = {}
        self.total_scores = {}
        self.recent_words = []

        # Player tracking
        self.active_powerups = {}  # {player_name: {powerup_name: True/False}}
        self.incorrect_guesses = {}  # {player_name: count of incorrect guesses this round}
        self.round_guess_order = []  # list of player names in order they guessed correctly
        self.round_start_time = None  # datetime when round started

        self.words = self.load_words()
        print(f"[Game] Loaded {len(self.words)} words.")

    # ===== Load words =====
    def load_words(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_words = []
        for category in data.values():
            if isinstance(category, list):
                for item in category:
                    if isinstance(item, dict) and "word" in item:
                        all_words.append(item)
        return all_words

    # ===== /gamestart =====
    @app_commands.command(name="gamestart", description="Start Guess the Word")
    async def gamestart(self, interaction: discord.Interaction):
        if self.game_running:
            await interaction.response.send_message("A game is already running.", ephemeral=True)
            return
        await interaction.response.send_message("🎮 Starting game...", ephemeral=True)
        self.game_running = True
        self.channel = interaction.channel
        self.starter = interaction.user

        self.round_scores = {}
        self.last_guess_colors = ""
        self.timer = 60
        self.round = 0
        self.used_hints = []
        self.active_powerups = {}
        self.incorrect_guesses = {}
        self.round_guess_order = []
        self.round_start_time = datetime.utcnow()

        await self.start_new_round()

    # ===== /stopgame =====
    @app_commands.command(name="stopgame", description="Stop the game")
    async def stopgame(self, interaction: discord.Interaction):
        if not self.game_running:
            await interaction.response.send_message("No game running.", ephemeral=True)
            return
        if interaction.user != self.starter:
            await interaction.response.send_message("Only the starter can stop the game.", ephemeral=True)
            return
        await interaction.response.send_message("🛑 Game stopped.", ephemeral=True)
        await self.end_game(manual=True)

    # ===== /leaderboard =====
    @app_commands.command(name="leaderboard", description="Show full leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        if not self.total_scores:
            await interaction.response.send_message("No scores yet.", ephemeral=True)
            return
        lines = [f"◡◡ 🏆 {player}: {score} Points ♡"
                 for player, score in sorted(self.total_scores.items(), key=lambda x: x[1], reverse=True)]
        embed = discord.Embed(color=0x1b1c23, description="\n".join(lines))
        await interaction.response.send_message(embed=embed)

    # ===== /hint =====
    @app_commands.command(name="hint", description="Get a hint for the current word")
    async def hint(self, interaction: discord.Interaction):
        player = interaction.user.name
        if not self.game_running or not self.word_entry:
            await interaction.response.send_message("No game is running. Use `/gamestart` to start!", ephemeral=True)
            return

        all_hints = [self.word_entry.get("hint1"), self.word_entry.get("hint2"), self.word_entry.get("hint3")]
        available_hints = [h for h in all_hints if h and h not in self.used_hints]

        if not available_hints:
            await interaction.response.send_message("No more hints available!", ephemeral=True)
            return

        hint_text = random.choice(available_hints)
        self.used_hints.append(hint_text)
        self.timer = max(self.timer - 10, 0)  # Deduct time as penalty for hint
        await self.send_round_embed()
        await interaction.response.send_message(f"Hint: {hint_text}", ephemeral=True)

    # ===== Timer loop =====
    async def timer_loop(self):
        try:
            while self.timer > 0 and self.game_running:
                await asyncio.sleep(1)
                self.timer -= 1
                if self.timer in (30, 15):
                    await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.timer} seconds remaining ⠀ּ ּ    ✧")
            if self.game_running:
                await self.end_game()
        except asyncio.CancelledError:
            return

    # ===== Message listener =====
    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.game_running or message.author.bot or message.channel != self.channel:
            return

        guess_raw = message.content
        guess = normalize(guess_raw)
        target = normalize(self.word)
        valid_words = [normalize(w["word"]) for w in self.words]
        if guess not in valid_words:
            return

        player = message.author.name
        if player not in self.active_powerups:
            # Initialize all automatic power-ups
            self.active_powerups[player] = {
                "reveal_letter": True,
                "hint_boost": True,
                "skip_timer": True,
                "streak_shield": True,
                "steal_point": True,
                "double_points": True,
                "triple_points": True,
                "point_steal": True,
                "streak_bonus": True,
                "fast_guess": True,
                "lucky_letter": True,
                "perfect_guess": True,
            }
            self.incorrect_guesses[player] = 0

        # ===== Wordle coloring =====
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
        self.last_guess_colors = "".join(colors)

        # ===== Automatic power-ups logic =====
        pu = self.active_powerups[player]
        points = 1

        # Incorrect guess power-ups
        if guess != target:
            self.incorrect_guesses[player] += 1
            # Reveal Letter
            if pu["reveal_letter"]:
                index_to_reveal = random.randint(0, len(target) - 1)
                self.word_display[index_to_reveal] = target[index_to_reveal]
                pu["reveal_letter"] = False
            # Hint Boost after 2 incorrect guesses
            if pu["hint_boost"] and self.incorrect_guesses[player] >= 2:
                all_hints = [self.word_entry.get("hint1"), self.word_entry.get("hint2"), self.word_entry.get("hint3")]
                self.used_hints = list({h for h in all_hints if h})
                pu["hint_boost"] = False
            await self.send_round_embed()
            return

        # Correct guess power-ups
        # Double / Triple points
        if pu["triple_points"]:
            points *= 3
            pu["triple_points"] = False
        elif pu["double_points"]:
            points *= 2
            pu["double_points"] = False

        # Fast guess bonus
        time_elapsed = (datetime.utcnow() - self.round_start_time).total_seconds()
        if pu["fast_guess"] and time_elapsed <= 15:
            points += 1
            pu["fast_guess"] = False

        # Streak bonus
        if pu["streak_bonus"] and player not in self.round_guess_order:
            points += 1
            pu["streak_bonus"] = False

        # Lucky letter bonus (first correct letter in round)
        if pu["lucky_letter"]:
            points += 1
            pu["lucky_letter"] = False

        # Perfect guess bonus
        if pu["perfect_guess"] and not self.used_hints:
            points += 1
            pu["perfect_guess"] = False

        # Apply points
        self.round_scores[player] = self.round_scores.get(player, 0) + points
        self.total_scores[player] = self.total_scores.get(player, 0) + points
        self.round_guess_order.append(player)

        # Steal point
        if pu["steal_point"]:
            for other in self.round_scores:
                if other != player:
                    self.round_scores[player] += 1
                    self.total_scores[player] += 1
                    pu["steal_point"] = False
                    break

        # Point steal
        if pu["point_steal"]:
            others = [p for p in self.round_scores if p != player]
            if others:
                victim = random.choice(others)
                if self.round_scores[victim] > 0:
                    self.round_scores[victim] -= 1
                    self.round_scores[player] += 1
                    self.total_scores[victim] -= 1
                    self.total_scores[player] += 1
            pu["point_steal"] = False

        await self.send_mini_leaderboard()
        await self.channel.send(f"🎉 {player} guessed the word correctly! (+{points} pts)")

        # Skip timer
        if pu["skip_timer"]:
            self.timer += 10
            pu["skip_timer"] = False

        await self.start_new_round()

    # ===== Start new round =====
    async def start_new_round(self):
        self.round += 1
        choices = [w for w in self.words if w["word"] not in self.recent_words]
        if not choices:
            self.recent_words = []
            choices = self.words

        self.word_entry = random.choice(choices)
        self.word = self.word_entry["word"]
        self.word_display = ["⬜"] * len(self.word)
        self.last_guess_colors = ""
        self.used_hints = []
        self.incorrect_guesses = {p: 0 for p in self.active_powerups}
        self.round_guess_order = []
        self.round_start_time = datetime.utcnow()

        self.recent_words.append(self.word)
        if len(self.recent_words) > 3:
            self.recent_words.pop(0)

        # Reset timer
        self.timer = 60
        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.timer_loop())

        await self.send_round_embed()

    # ===== Round embed =====
    async def send_round_embed(self):
        word_line = self.last_guess_colors if self.last_guess_colors else "".join(self.word_display)
        streak = max(self.round_scores.values(), default=0)
        embed = discord.Embed(color=0x1b1c23)
        embed.description = (
            f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟ Round {self.round} ꒱ᣟᣟ\n"
            f"﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚ | {self.timer}s\n"
            f"♩  ﹒ ﹒  Streak  ﹒ ୨୧ | 🔥 {streak}\n\n"
            f"{word_line}\n\n"
            f"⃕⠀⠀Timer 𓂃　۪ ׄ\n"
            f"{'❤️'*5}\n\n"
            f"⃕⠀⠀starter hint 𓂃　۪ ׄ\n{self.word_entry.get('start_hint','No hint')}\n\n"
            f"⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ\n{'None' if not self.used_hints else '\\n'.join(self.used_hints)}\n\n"
            f"♡ Power-Ups ♡\n"
        )
        for player, pu in self.active_powerups.items():
            active = [k.replace("_", " ").title() for k, v in pu.items() if v]
            if active:
                embed.description += f"{player}: {', '.join(active)}\n"

        await self.channel.send(embed=embed)

    # ===== Mini leaderboard =====
    async def send_mini_leaderboard(self):
        lines = []
        for player, score in sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"◡◡ 🏆 {player} : {score} Points ♡")
        if lines:
            embed = discord.Embed(color=0x1b1c23, description="\n".join(lines))
            await self.channel.send(embed=embed)

    # ===== End game =====
    async def end_game(self, manual=False):
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

        embed = discord.Embed(color=0x1b1c23)
        embed.add_field(
            name="˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ",
            value=f"The word was: **{self.word}**\nUse /gamestart to play again",
            inline=False,
        )
        await self.channel.send(embed=embed)
        self.reset_game()

    # ===== Reset game =====
    def reset_game(self):
        self.game_running = False
        self.word_entry = None
        self.word = ""
        self.word_display = []
        self.channel = None
        self.starter = None
        self.used_hints = []
        self.round_scores = {}
        self.last_guess_colors = ""
        self.round = 0
        self.active_powerups = {}
        self.incorrect_guesses = {}
        self.round_guess_order = []
        self.round_start_time = None
        self.timer = 60
        self.timer_task = None

# ===== Setup =====
async def setup(bot):
    await bot.add_cog(Game(bot))