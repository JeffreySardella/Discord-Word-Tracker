import discord
import io
import os
import re
from collections import Counter
from dotenv import load_dotenv
from faster_whisper import WhisperModel

load_dotenv()

# --- CONFIGURATION ---
MODEL_SIZE = "base.en"  # or "small.en" for higher accuracy (~500MB RAM)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 446051370802479115

model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(intents=intents)

holiday_mode = False


async def finished_callback(sink, channel: discord.TextChannel, *args):
    if holiday_mode:
        await channel.send("🎄 *Ho ho ho! Let's see what everyone said...* 🎅")
        header = "### 🎁 Holiday Word Report 🎁\n"
        no_audio_msg = "🦌 *The reindeer heard nothing!*"
        no_speech_fmt = "🎅 *Silent Night...*"
        top_label = "🎄 Top words"
    else:
        await channel.send("Recording finished. Processing audio...")
        header = "### Voice Chat Summary\n"
        no_audio_msg = "No audio detected."
        no_speech_fmt = "(No speech detected)"
        top_label = "Top words"

    report = header
    any_audio = False

    for user_id, audio in sink.audio_data.items():
        user = bot.get_user(user_id) or await bot.fetch_user(user_id)
        username = user.display_name

        audio_bytes = audio.file.read()
        if len(audio_bytes) < 1000:
            continue

        any_audio = True
        segments, _ = model.transcribe(io.BytesIO(audio_bytes), beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()

        if text:
            words = re.findall(r"\b[a-z']+\b", text.lower())
            word_count = len(words)
            top_words = Counter(words).most_common(10)
            top_str = ", ".join(f"{w} ({c})" for w, c in top_words)
            report += f"**{username}** *({word_count} words)*\n"
            report += f"┗ {top_label}: {top_str}\n\n"
        else:
            report += f"**{username}**: {no_speech_fmt}\n\n"

    if not any_audio:
        await channel.send(no_audio_msg)
    else:
        await channel.send(report)


@bot.slash_command(guild_ids=[GUILD_ID], description="Start tracking voice chat")
async def start(ctx: discord.ApplicationContext):
    if not ctx.author.voice:
        return await ctx.respond("You must be in a voice channel!")

    if ctx.voice_client:
        if ctx.voice_client.recording:
            return await ctx.respond("Already recording.")
        ctx.voice_client.start_recording(
            discord.sinks.WaveSink(), finished_callback, ctx.channel
        )
    else:
        vc = await ctx.author.voice.channel.connect()
        vc.start_recording(discord.sinks.WaveSink(), finished_callback, ctx.channel)

    msg = "🎄 Ho ho ho! Now tracking who says what..." if holiday_mode else "Now listening to all users in VC..."
    await ctx.respond(msg)


@bot.slash_command(guild_ids=[GUILD_ID], description="Stop tracking and show results")
async def stop(ctx: discord.ApplicationContext):
    if ctx.voice_client and ctx.voice_client.recording:
        msg = "🎅 Wrapping up your gifts..." if holiday_mode else "Stopping recording and analyzing..."
        await ctx.respond(msg)
        ctx.voice_client.stop_recording()
    else:
        await ctx.respond("I am not currently recording.")


@bot.slash_command(guild_ids=[GUILD_ID], description="Disconnect the bot from voice")
async def leave(ctx: discord.ApplicationContext):
    if ctx.voice_client:
        if ctx.voice_client.recording:
            ctx.voice_client.stop_recording()
        await ctx.voice_client.disconnect()
        await ctx.respond("Disconnected.")
    else:
        await ctx.respond("I am not in a voice channel.")


@bot.slash_command(guild_ids=[GUILD_ID], description="Toggle holiday (Christmas) mode")
async def holiday(ctx: discord.ApplicationContext):
    global holiday_mode
    holiday_mode = not holiday_mode
    if holiday_mode:
        await ctx.respond("🎄 Holiday mode ON! Ho ho ho!")
    else:
        await ctx.respond("Holiday mode off.")


bot.run(BOT_TOKEN)
