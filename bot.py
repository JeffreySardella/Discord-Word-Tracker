import discord
from discord.ext import tasks
import io
import os
import re
import datetime
from collections import Counter
from dotenv import load_dotenv
from faster_whisper import WhisperModel

load_dotenv()

# --- CONFIGURATION ---
MODEL_SIZE = "base.en"  # or "small.en" for higher accuracy (~500MB RAM)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 446051370802479115

# Channel where all word reports are posted (set in .env, restrict this channel's permissions in Discord)
SUMMARY_CHANNEL_ID = int(os.getenv("SUMMARY_CHANNEL_ID", "0")) or None

# Comma-separated role IDs that can use /join and /leave (leave blank to allow everyone)
_mod_role_env = os.getenv("MOD_ROLE_IDS", "")
MOD_ROLE_IDS = [int(x.strip()) for x in _mod_role_env.split(",") if x.strip()]

# Words tracked for the profanity/slur report
FLAGGED_WORDS = {
    # Profanity
    "fuck", "fucking", "fucker", "fucked", "fucks", "motherfucker", "motherfucking",
    "shit", "shitting", "shitter", "bullshit",
    "ass", "asshole", "asses",
    "bitch", "bitches", "bitching",
    "bastard", "bastards",
    "damn", "goddamn",
    "crap",
    "dick", "dicks",
    "cock", "cocks",
    "pussy", "pussies",
    "cunt", "cunts",
    "piss", "pissed",
    "whore", "whores",
    "slut", "sluts",
    "twat", "twats",
    # Slurs (tracked for moderation purposes)
    "nigger", "nigga", "faggot", "fag", "retard", "retarded",
    "spic", "kike", "chink", "gook", "wetback",
    "dyke", "tranny",
}

model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(intents=intents)

holiday_mode = False
daily_word_counts: dict[int, Counter] = {}  # user_id -> Counter of all words today
daily_usernames: dict[int, str] = {}        # user_id -> display name
_disconnect_after = False                    # set by /leave before stop_recording()
_summary_channel_id = SUMMARY_CHANNEL_ID    # updated to last /join channel if not configured


def has_mod_role(ctx: discord.ApplicationContext) -> bool:
    """Returns True if the user has a permitted role (or no restriction is configured)."""
    if not MOD_ROLE_IDS:
        return True
    return any(role.id in MOD_ROLE_IDS for role in ctx.author.roles)


async def get_summary_channel(fallback: discord.TextChannel) -> discord.TextChannel:
    if _summary_channel_id:
        ch = bot.get_channel(_summary_channel_id)
        if ch:
            return ch
    return fallback


def build_word_report(
    user_stats: list[tuple],
    header: str,
    top_label: str,
) -> tuple[str, str | None]:
    """
    user_stats: list of (username, total_words, top_words, swear_counts)
    Returns (main_report, swear_report_or_None)
    """
    report = header
    swear_lines = []

    for username, total_words, top_words, swear_counts in user_stats:
        if total_words == 0:
            report += f"**{username}**: *(No speech detected)*\n\n"
            continue
        top_str = ", ".join(f"{w} ({c})" for w, c in top_words)
        report += f"**{username}** *({total_words} words)*\n┗ {top_label}: {top_str}\n\n"

        if swear_counts:
            sorted_swears = sorted(swear_counts.items(), key=lambda x: -x[1])
            swear_str = ", ".join(f"{w} ({c})" for w, c in sorted_swears)
            total_flagged = sum(swear_counts.values())
            swear_lines.append(f"**{username}** *({total_flagged} flagged)*: {swear_str}")

    swear_report = None
    if swear_lines:
        swear_report = "### ⚠️ Profanity & Slur Report\n" + "\n".join(swear_lines)

    return report, swear_report


async def finished_callback(sink: discord.sinks.WaveSink, channel: discord.TextChannel):
    global _disconnect_after
    should_disconnect = _disconnect_after
    _disconnect_after = False

    summary_ch = await get_summary_channel(channel)

    if holiday_mode:
        await summary_ch.send("🎄 *Ho ho ho! Let's see what everyone said...* 🎅")
        header = "### 🎁 Holiday Word Report 🎁\n"
        top_label = "🎄 Top words"
    else:
        await summary_ch.send("Recording finished. Processing audio...")
        header = "### Voice Chat Summary\n"
        top_label = "Top words"

    any_audio = False
    user_stats = []

    for user_id, audio in sink.audio_data.items():
        user = bot.get_user(user_id) or await bot.fetch_user(user_id)
        username = user.display_name

        audio_bytes = audio.file.read()
        if len(audio_bytes) < 1000:
            continue

        any_audio = True
        segments, _ = model.transcribe(io.BytesIO(audio_bytes), beam_size=5)
        text = " ".join(seg.text for seg in segments).strip()

        if text:
            words = re.findall(r"\b[a-z']+\b", text.lower())
            counter = Counter(words)
            top_words = counter.most_common(10)
            swear_counts = {w: c for w, c in counter.items() if w in FLAGGED_WORDS}

            user_stats.append((username, len(words), top_words, swear_counts))

            # Accumulate into daily totals
            if user_id not in daily_word_counts:
                daily_word_counts[user_id] = Counter()
            daily_word_counts[user_id].update(words)
            daily_usernames[user_id] = username
        else:
            user_stats.append((username, 0, [], {}))

    if not any_audio:
        no_audio = "🦌 *The reindeer heard nothing!*" if holiday_mode else "No audio detected."
        await summary_ch.send(no_audio)
    else:
        report, swear_report = build_word_report(user_stats, header, top_label)
        await summary_ch.send(report)
        if swear_report:
            await summary_ch.send(swear_report)

    if should_disconnect and channel.guild.voice_client:
        await channel.guild.voice_client.disconnect()


@tasks.loop(time=datetime.time(hour=0, minute=0))  # midnight UTC
async def daily_summary_task():
    if not daily_word_counts:
        return

    ch = bot.get_channel(_summary_channel_id) if _summary_channel_id else None
    if not ch:
        return

    # Sort by most words spoken
    sorted_users = sorted(daily_word_counts.items(), key=lambda x: -sum(x[1].values()))
    user_stats = []
    for user_id, counter in sorted_users:
        username = daily_usernames.get(user_id, str(user_id))
        total = sum(counter.values())
        top_words = counter.most_common(10)
        swear_counts = {w: c for w, c in counter.items() if w in FLAGGED_WORDS}
        user_stats.append((username, total, top_words, swear_counts))

    report, swear_report = build_word_report(
        user_stats,
        "### 📊 Daily Word Leaderboard\n",
        "Top words",
    )
    await ch.send(report)
    if swear_report:
        await ch.send(swear_report)

    daily_word_counts.clear()
    daily_usernames.clear()


@daily_summary_task.before_loop
async def before_daily_summary():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    daily_summary_task.start()
    print(f"Logged in as {bot.user}")


@bot.slash_command(guild_ids=[GUILD_ID], description="Join voice chat and start tracking words")
async def join(ctx: discord.ApplicationContext):
    if not has_mod_role(ctx):
        return await ctx.respond("You don't have permission to use this command.", ephemeral=True)
    if not ctx.author.voice:
        return await ctx.respond("You must be in a voice channel!", ephemeral=True)

    # If no summary channel is configured, use the current channel
    global _summary_channel_id
    if not SUMMARY_CHANNEL_ID:
        _summary_channel_id = ctx.channel.id

    if ctx.voice_client:
        if ctx.voice_client.recording:
            return await ctx.respond("Already recording.", ephemeral=True)
        ctx.voice_client.start_recording(
            discord.sinks.WaveSink(), finished_callback, ctx.channel
        )
    else:
        vc = await ctx.author.voice.channel.connect()
        vc.start_recording(discord.sinks.WaveSink(), finished_callback, ctx.channel)

    msg = "🎄 Ho ho ho! Listening..." if holiday_mode else "Joined! Now listening to all users in VC..."
    await ctx.respond(msg)


@bot.slash_command(guild_ids=[GUILD_ID], description="Stop tracking and leave voice chat")
async def leave(ctx: discord.ApplicationContext):
    if not has_mod_role(ctx):
        return await ctx.respond("You don't have permission to use this command.", ephemeral=True)

    if ctx.voice_client and ctx.voice_client.recording:
        global _disconnect_after
        _disconnect_after = True
        msg = "🎅 Wrapping up your gifts..." if holiday_mode else "Stopping and analyzing..."
        await ctx.respond(msg)
        ctx.voice_client.stop_recording()
    elif ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.respond("Disconnected.")
    else:
        await ctx.respond("I am not in a voice channel.")


@bot.slash_command(guild_ids=[GUILD_ID], description="Toggle holiday (Christmas) mode")
async def holiday(ctx: discord.ApplicationContext):
    if not has_mod_role(ctx):
        return await ctx.respond("You don't have permission to use this command.", ephemeral=True)
    global holiday_mode
    holiday_mode = not holiday_mode
    if holiday_mode:
        await ctx.respond("🎄 Holiday mode ON! Ho ho ho!")
    else:
        await ctx.respond("Holiday mode off.")


bot.run(BOT_TOKEN)
