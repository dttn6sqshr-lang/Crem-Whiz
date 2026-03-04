import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, random, os, asyncio, re
from datetime import datetime

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/words.json")
GUESS_CHANNEL_NAME = "guess﹒le﹒word﹒⊂⊃﹒"
LOG_CHANNEL_NAME = "ᐢᗜᐢ﹑logs！﹒"

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
        self.round_scores = {}   # points for this round
        self.total_scores = {}   # points across rounds
        self.recent_words = []
        self.incorrect_guesses = {}
        self.round_guess_order = []

        self.words = self.load_words()
        self.guess_purger_task.start()

    # ================= Load Words =================
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

    # ================= SEND LOG =================
    async def send_log(self, title, main_line, detail_line):
        log_channel = discord.utils.get(self.bot.get_all_channels(), name=LOG_CHANNEL_NAME)
        if not log_channel:
            return
        embed = discord.Embed(color=0x1b1c23, timestamp=datetime.utcnow())
        embed.title = f"Ი ⁠ᰍ៸៸　　{title}"
        embed.description = f"　　　　　　　{main_line} ೀ 𝄄𝄄　 ۪‎      ‎ ࣪ 　\n　　　　　　　𐔌 ̣̣ {detail_line}"
        await log_channel.send(embed=embed)

    # ================= /gamestart =================
    @app_commands.command(name="gamestart", description="Start Guess the Word")
    async def gamestart(self, interaction: discord.Interaction):
        if self.game_running:
            await interaction.response.send_message("A game is already running.", ephemeral=True)
            await self.send_log("Game Start Blocked",
                                f"{interaction.user.name} tried to start a game",
                                f"Server: {interaction.guild.name} | Channel: {interaction.channel.name}")
            return

        await interaction.response.defer()
        self.game_running = True
        self.channel = interaction.channel
        self.starter = interaction.user

        self.round_scores = {}
        self.last_guess_colors = ""
        self.timer = 60
        self.round = 0
        self.used_hints = []
        self.incorrect_guesses = {}
        self.round_guess_order = []

        await self.send_log("Game Started",
                            f"Started by {interaction.user.name}",
                            f"Server: {interaction.guild.name} | Channel: {interaction.channel.name}")

        await self.start_new_round()

    # ================= /stopgame =================
    @app_commands.command(name="stopgame", description="Stop the game")
    async def stopgame(self, interaction: discord.Interaction):
        if not self.game_running:
            await interaction.response.send_message("No game running.", ephemeral=True)
            return
        if interaction.user != self.starter:
            await interaction.response.send_message("Only the starter can stop the game.", ephemeral=True)
            return
        await interaction.response.send_message("🛑 Game stopped.", ephemeral=True)
        await self.send_log("Game Stopped",
                            f"Stopped by {interaction.user.name}",
                            f"Server: {interaction.guild.name} | Channel: {interaction.channel.name}")
        await self.end_game(manual=True)

    # ================= /leaderboard =================
    @app_commands.command(name="leaderboard", description="Show full leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        if not self.total_scores:
            await interaction.response.send_message("No scores yet.", ephemeral=True)
            return
        lines = [f"◡◡ 🏆 {player}: {score} Points ♡"
                 for player, score in sorted(self.total_scores.items(), key=lambda x: x[1], reverse=True)]
        embed = discord.Embed(color=0x1b1c23, description="\n".join(lines))
        await interaction.response.send_message(embed=embed)

    # ================= /hint =================
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
        self.timer = max(self.timer - 10, 0)
        await self.send_round_embed()
        await interaction.response.send_message(f"Hint:\n{hint_text}", ephemeral=True)
        await self.send_log("Hint Used",
                            f"{player} used a hint",
                            f"Server: {interaction.guild.name} | Channel: {interaction.channel.name} | Round {self.round}")

    # ================= Timer Loop =================
    async def timer_loop(self):
        try:
            while self.timer > 0 and self.game_running:
                await asyncio.sleep(1)
                self.timer -= 1
                if self.timer in (30, 15):
                    await self.channel.send(f"⠀ꕀ⠀⠀⠀ׄ⠀⠀ִ⠀ {self.timer} seconds remaining ⠀ּ ּ    ✧")
                    await self.send_log("Timer Warning",
                                        f"{self.timer}s remaining",
                                        f"Server: {self.channel.guild.name} | Channel: {self.channel.name} | Round {self.round}")
            if self.game_running:
                await self.channel.send("⏰ Time's up!")
                await self.send_log("Game Ended (Timer)",
                                    f"Time ran out",
                                    f"Server: {self.channel.guild.name} | Channel: {self.channel.name} | Round {self.round}")
                await self.end_game()
        except asyncio.CancelledError:
            return

    # ================= On Message Listener =================
    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.game_running or message.author.bot or message.channel != self.channel:
            return

        guess = normalize(message.content)
        target = normalize(self.word)
        valid_words = [normalize(w["word"]) for w in self.words]

        if guess not in valid_words:
            return

        player = message.author.name
        self.incorrect_guesses[player] = self.incorrect_guesses.get(player, 0)

        # Wordle coloring (even if wrong)
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

        correct = False
        if guess == target:
            self.round_scores[player] = self.round_scores.get(player, 0) + 1
            self.total_scores[player] = self.total_scores.get(player, 0) + 1
            self.round_guess_order.append(player)
            correct = True
            await self.channel.send(f"🎉 {player} guessed the word correctly! (+1 pt)")

        # Only send embed for incorrect guesses
        if not correct:
            await self.send_round_embed()

        await self.send_log("Guess",
                            f"{player} guessed {'correctly' if correct else 'wrong'}",
                            f"Server: {self.channel.guild.name} | Channel: {self.channel.name} | Round {self.round}")

        if correct:
            await self.start_new_round()

    # ================= Start New Round =================
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
        self.incorrect_guesses = {p: 0 for p in self.round_scores}
        self.round_guess_order = []

        self.recent_words.append(self.word)
        if len(self.recent_words) > 3:
            self.recent_words.pop(0)

        # Reset timer
        self.timer = 60
        if self.timer_task:
            self.timer_task.cancel()
            try:
                await self.timer_task
            except asyncio.CancelledError:
                pass
        self.timer_task = asyncio.create_task(self.timer_loop())

        await self.send_round_embed()
        await self.send_log("Round Started",
                            f"Round {self.round} started",
                            f"Server: {self.channel.guild.name} | Channel: {self.channel.name}")

    # ================= Round Embed =================
    async def send_round_embed(self):
        word_line = self.last_guess_colors if self.last_guess_colors else "".join(self.word_display)
        streak = max(self.round_scores.values(), default=0)
        hints_display = "\n".join(self.used_hints) if self.used_hints else "None"

        leaderboard_lines = []
        for player, score in sorted(self.round_scores.items(), key=lambda x: x[1], reverse=True):
            leaderboard_lines.append(f"◡◡ 🏆 {player}: {score} Points ♡")

        embed = discord.Embed(color=0x1b1c23)
        embed.description = (
            f"ᰍ   ⟡   ꒰ Guess the Word ꒱   |   ᣟᣟ Round {self.round} ꒱ᣟᣟ\n"
            f"﹒🍥﹒  ୧  Time Left   ﹒♡﹒  ˚ | {self.timer}s\n"
            f"♩  ﹒ ﹒  Streak  ﹒ ୨୧ | 🔥 {streak}\n\n"
            f"{word_line}\n\n"
            f"⃕⠀⠀Timer 𓂃　۪ ׄ\n"
            f"{'❤️' * max(5 - max(self.incorrect_guesses.values(), default=0), 0)}{'🖤' * max(max(self.incorrect_guesses.values(), default=0),0)}\n\n"
            f"⃕⠀⠀starter hint 𓂃　۪ ׄ\n{self.word_entry.get('start_hint','No hint')}\n\n"
            f"⠀♡⃕⠀⠀used hints 𓂃　۪ ׄ\n{hints_display}\n\n"
            f"Mini Leaderboard:\n" + ("\n".join(leaderboard_lines) if leaderboard_lines else "No scores yet")
        )
        await self.channel.send(embed=embed)

    # ================= End Game =================
    async def end_game(self, manual=False):
        if self.timer_task:
            self.timer_task.cancel()
            try:
                await self.timer_task
            except asyncio.CancelledError:
                pass
            self.timer_task = None

        self.game_running = False

        embed = discord.Embed(color=0x1b1c23)
        if not manual:
            embed.add_field(
                name="˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ",
                value=f"The word was: **{self.word}**\nUse /gamestart to play again",
                inline=False,
            )
        else:
            embed.add_field(
                name="˚⠀⠀♡⃕⠀⠀game over 𓂃　۪ ׄ",
                value="Game stopped manually.\nUse /gamestart to play again",
                inline=False,
            )
        await self.channel.send(embed=embed)
        self.reset_game()

    # ================= Reset Game =================
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
        self.incorrect_guesses = {}
        self.round_guess_order = []
        self.timer = 60
        self.timer_task = None

    # ================= 2-Hour Guess Channel Purger =================
    @tasks.loop(hours=2)
    async def guess_purger_task(self):
        await self.bot.wait_until_ready()
        channel = discord.utils.get(self.bot.get_all_channels(), name=GUESS_CHANNEL_NAME)
        if channel and not self.game_running:
            deleted = await channel.purge(limit=100, check=lambda m: not m.pinned)
            await self.send_log(
                "Channel Purged (2h)",
                f"{channel.name} purged {len(deleted)} messages",
                f"Server: {channel.guild.name}"
            )


# ================= Setup =================
async def setup(bot):
    await bot.add_cog(Game(bot))