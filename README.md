# Discord Voice Chat Word Tracker

A Discord bot that records voice chat, transcribes each user's speech locally, and posts a per-user word count and top 10 most-used words to a text channel.

No audio is sent to any external API — all transcription runs locally on your CPU.

---

## How It Works

1. Use `/start` to have the bot join your voice channel and begin recording.
2. Each user's audio is captured in a separate stream automatically.
3. Use `/stop` to end the session — the bot transcribes all audio and posts a summary. It stays in the VC.
4. Use `/leave` when you want the bot to disconnect.

---

## Commands

| Command | Description |
|---|---|
| `/start` | Join your voice channel and begin a recording session. |
| `/stop` | End the session and post the word summary. Bot stays in VC. |
| `/leave` | Disconnect the bot from the voice channel. |
| `/holiday` | Toggle Christmas-themed messages on/off. |

---

## Setup

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
```

**Discord Developer Portal:**
- Create a bot and copy its token
- Enable the `Server Members Intent` under Privileged Gateway Intents
- Grant permissions: `Connect`, `Speak`, `Use Voice Activity`, `Send Messages`

**Token:** Create a `.env` file in the project root:

```
BOT_TOKEN=your_token_here
```

---

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `MODEL_SIZE` | `"base.en"` | Fast, ~150MB RAM. Use `"small.en"` for higher accuracy (~500MB RAM). |
| `GUILD_ID` | your server ID | Ensures slash commands register instantly to your server. |

Runs on CPU with int8 quantization — no GPU required.

---

## Output Example

```
### Voice Chat Summary
**Alice** (13 words)
┗ Top words: the (3), just (2), hey (1), everyone (1), wanted (1), check (1), project (1), status (1)

**Bob** (12 words)
┗ Top words: the (2), yeah (1), finished (1), backend (1), yesterday (1), need (1), write (1), tests (1)

**Charlie**: (No speech detected)
```

### Holiday Mode

```
🎁 Holiday Word Report 🎁
**Alice** (13 words)
┗ 🎄 Top words: the (3), just (2), hey (1), everyone (1) ...

**Charlie**: 🎅 Silent Night...
```

---

## Stack

- **[Pycord](https://github.com/Pycord-Development/pycord)** — Discord library with built-in per-user voice recording sinks
- **[Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)** — CTranslate2-optimized Whisper for fast local transcription
