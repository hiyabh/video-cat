# VideoCat

Turn long videos into short viral clips with auto-subtitles — locally on your machine.

## Features

- **Auto-transcription** — faster-whisper (local, free, supports Hebrew/English/Arabic/Spanish/French)
- **Smart clip detection** — LLM analyzes transcript to find viral-worthy moments
  - **Ollama + Llama 3.2 3B** (local, free, ~2GB RAM) — default
  - **Claude / GPT** (cloud, higher quality)
- **Auto-subtitles** — burned onto video with word-by-word animation (ASS format)
- **Format presets** — 9:16 (TikTok/Reels), 1:1 (Instagram), 16:9 (YouTube)
- **Background music** — mix any audio at adjustable volume
- **Logo overlay** — position anywhere with transparency
- **Custom fonts** — load TTF/OTF for subtitle styling
- **GUI + CLI** — visual interface or command-line for automation

## Requirements

- Python 3.11+
- FFmpeg installed and in PATH
- **Ollama** (optional, for local LLM) — https://ollama.com

## Setup

```bash
# Clone
git clone https://github.com/hiyabh/video-cat.git
cd video-cat

# Install dependencies
pip install -r requirements.txt

# Install Ollama + model (for local LLM, no API key needed)
# Download Ollama from https://ollama.com
ollama pull llama3.2:3b

# Configure
cp .env.example .env
# Default uses Ollama (local). Edit .env to switch to Claude/GPT.
```

## Usage

### GUI
```bash
python run_gui.py
```

### CLI
```bash
# Basic — auto-detect language, 5 clips, vertical format
python run_cli.py path/to/video.mp4

# Custom options
python run_cli.py video.mp4 -f square -n 3 -l he --music bg.mp3 --logo logo.png

# All options
python run_cli.py video.mp4 \
  --format vertical \
  --max-clips 5 \
  --min-duration 15 \
  --max-duration 90 \
  --language auto \
  --model base \
  --music path/to/music.mp3 \
  --logo path/to/logo.png \
  --font path/to/font.ttf \
  --font-size 28 \
  --no-animate
```

## Output

Clips are saved to `output/<video_name>/`:
```
output/
  my_video/
    my_video.srt            # Full transcript
    clip_01_catchy_title.mp4
    clip_02_another_clip.mp4
    ...
```

## How It Works

1. **Transcribe** — faster-whisper converts speech to text with timestamps
2. **Detect** — LLM (Claude/GPT) analyzes transcript, picks engaging segments
3. **Cut** — FFmpeg cuts video at precise timestamps
4. **Subtitle** — ASS subtitles with word-by-word karaoke animation
5. **Format** — Scale/crop to target aspect ratio
6. **Overlay** — Add music, logo, custom fonts

## Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BACKEND` | `ollama` | `ollama` / `anthropic` / `openai` / `none` |
| `OLLAMA_MODEL` | `llama3.2:3b` | Local model via Ollama |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `ANTHROPIC_API_KEY` | — | Claude API key (if using cloud) |
| `OPENAI_API_KEY` | — | GPT API key (if using cloud) |
| `WHISPER_MODEL` | `base` | Whisper model (tiny/base/small/medium/large-v3) |
| `DEFAULT_LANGUAGE` | `auto` | Language code or auto-detect |
| `MAX_CLIPS` | `5` | Max clips per video |
| `MIN_CLIP_DURATION` | `15` | Min clip length (seconds) |
| `MAX_CLIP_DURATION` | `90` | Max clip length (seconds) |
| `DEFAULT_FORMAT` | `vertical` | vertical / square / horizontal |

## Distribution — Build EXE + Installer

For distributing to non-technical users, VideoCat can be packaged as a Windows installer:

### Prerequisites
- Python + dependencies (`pip install -r requirements.txt`)
- FFmpeg installed (will be bundled automatically)
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (for installer, optional)

### Build
```bash
build.bat
```

Output:
- `dist\VideoCat\VideoCat.exe` — standalone app folder (~680MB, includes FFmpeg + Whisper)
- `dist\VideoCat_Setup.exe` — single-file installer with setup wizard

### What the installer does
1. Installs VideoCat to Program Files
2. Creates desktop shortcut + Start menu entry
3. Prompts user to download [Ollama](https://ollama.com) (required for local AI)
4. On first run — auto-downloads Llama 3.2 3B model (~2GB, one-time)

### What the end user needs
- Windows 10/11 (x64)
- 4GB RAM minimum (8GB recommended)
- ~5GB disk space (app + model + Ollama)
- Internet connection on first run (to download Ollama + model)

After first run — **fully offline**. No API keys, no internet required.

## Tech Stack

- **faster-whisper** — local speech-to-text (CTranslate2)
- **FFmpeg** — video processing, subtitles, audio mixing
- **Ollama + Llama 3.2 3B** — local LLM for clip selection (default)
- **Claude / GPT** — optional cloud LLM for higher quality
- **CustomTkinter** — modern dark-theme GUI
