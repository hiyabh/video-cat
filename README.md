# VideoCat

Turn long videos into short viral clips with auto-subtitles — locally on your machine.

## Features

- **Auto-transcription** — faster-whisper (local, free, supports Hebrew/English/Arabic/Spanish/French)
- **Smart clip detection** — LLM analyzes transcript to find viral-worthy moments
- **Auto-subtitles** — burned onto video with word-by-word animation (ASS format)
- **Format presets** — 9:16 (TikTok/Reels), 1:1 (Instagram), 16:9 (YouTube)
- **Background music** — mix any audio at adjustable volume
- **Logo overlay** — position anywhere with transparency
- **Custom fonts** — load TTF/OTF for subtitle styling
- **GUI + CLI** — visual interface or command-line for automation

## Requirements

- Python 3.11+
- FFmpeg installed and in PATH

## Setup

```bash
# Clone
git clone https://github.com/hiyabh/video-cat.git
cd video-cat

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — add your Anthropic or OpenAI API key
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
| `ANTHROPIC_API_KEY` | — | Claude API key for clip detection |
| `OPENAI_API_KEY` | — | Alternative: GPT API key |
| `WHISPER_MODEL` | `base` | Whisper model (tiny/base/small/medium/large-v3) |
| `DEFAULT_LANGUAGE` | `auto` | Language code or auto-detect |
| `MAX_CLIPS` | `5` | Max clips per video |
| `MIN_CLIP_DURATION` | `15` | Min clip length (seconds) |
| `MAX_CLIP_DURATION` | `90` | Max clip length (seconds) |
| `DEFAULT_FORMAT` | `vertical` | vertical / square / horizontal |

## Tech Stack

- **faster-whisper** — local speech-to-text (CTranslate2)
- **FFmpeg** — video processing, subtitles, audio mixing
- **Claude / GPT** — intelligent clip selection
- **CustomTkinter** — modern dark-theme GUI
