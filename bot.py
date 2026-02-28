import discord
import io
import os
from dotenv import load_dotenv
from faster_whisper import WhisperModel

load_dotenv()

# --- CONFIGURATION ---
MODEL_SIZE = "base.en"  # or "small.en" for higher accuracy (~500MB RAM)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 446051370802479115

model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

intents = discord.Intents.default()
intents.members = True  # Required to resolve User IDs to display names
bot = discord.Bot(intents=intents)


async def finished_callback(sink, channel: discord.TextChannel, *args):
    await channel.send("Recording finished. Processing audio...")

    report = "### Voice Chat Summary\n"
    any_audio = False

    for user_id, audio in sink.audio_data.items():
        user = bot.get_user(user_id) or await bot.fetch_user(user_id)
        username = user.display_name

        audio_bytes = audio.file.read()
        if len(audio_bytes) < 1000:  # Skip silent/empty streams
            continue

        any_audio = True
        segments, _ = model.transcribe(io.BytesIO(audio_bytes), beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()

        if text:
            word_count = len(text.split())
            report += f"**{username}**: {text} *({word_count} words)*\n"
        else:
            report += f"**{username}**: (No speech detected)\n"

    if not any_audio:
        await channel.send("No audio detected.")
    else:
        await channel.send(report)


@bot.slash_command(guild_ids=[GUILD_ID], description="Start tracking voice chat")
async def start(ctx: discord.ApplicationContext):
    if not ctx.author.voice:
        return await ctx.respond("You must be in a voice channel!")

    if ctx.voice_client:
        if ctx.voice_client.recording:
            return await ctx.respond("Already recording.")
        # Already in VC, just start recording
        ctx.voice_client.start_recording(
            discord.sinks.WaveSink(), finished_callback, ctx.channel
        )
    else:
        vc = await ctx.author.voice.channel.connect()
        vc.start_recording(discord.sinks.WaveSink(), finished_callback, ctx.channel)

    await ctx.respond("Now listening to all users in VC...")


@bot.slash_command(guild_ids=[GUILD_ID], description="Stop tracking and show results")
async def stop(ctx: discord.ApplicationContext):
    if ctx.voice_client and ctx.voice_client.recording:
        await ctx.respond("Stopping recording and analyzing...")
        ctx.voice_client.stop_recording()
        # Bot stays in VC — use /leave to disconnect
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


bot.run(BOT_TOKEN)
