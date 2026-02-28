# Discord Voice Chat Word Tracker

A Discord bot that records voice chat, transcribes each user's speech locally, and posts a per-user word count and transcript summary to a text channel.

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
| `/stop` | End the session and post the transcript summary. Bot stays in VC. |
| `/leave` | Disconnect the bot from the voice channel. |

---

## Setup

**Requirements:** Python 3.10+

```bash
pip install "py-cord[voice]" faster-whisper
```

**Discord Developer Portal:**
- Create a bot and copy its token
- Enable the `Server Members Intent`
- Grant permissions: `Connect`, `Speak`, `Use Voice Activity`, `Send Messages`

**In the script**, replace `"YOUR_BOT_TOKEN"` with your actual token.

---

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `MODEL_SIZE` | `"base.en"` | Fast, ~150MB RAM. Use `"small.en"` for higher accuracy (~500MB RAM). |

Runs on CPU with int8 quantization — no GPU required.

---

## Output Example

```
### Voice Chat Summary
**Alice**: Hey everyone, just wanted to check in on the project status. (13 words)
**Bob**: Yeah I finished the backend yesterday, still need to write tests. (12 words)
**Charlie**: (No speech detected)
```

---

## Stack

- **[Pycord](https://github.com/Pycord-Development/pycord)** — Discord library with built-in per-user voice recording sinks
- **[Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)** — CTranslate2-optimized Whisper for fast local transcription
