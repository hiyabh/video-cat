"""Configuration management for VideoCat."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"
FONTS_DIR = PROJECT_ROOT / "fonts"
MUSIC_DIR = PROJECT_ROOT / "music"


@dataclass
class Config:
    # LLM
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    llm_backend: str = os.getenv("LLM_BACKEND", "ollama")  # ollama | anthropic | openai | none

    # Whisper
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    default_language: str = os.getenv("DEFAULT_LANGUAGE", "auto")

    # Clip settings
    max_clips: int = int(os.getenv("MAX_CLIPS", "5"))
    min_clip_duration: int = int(os.getenv("MIN_CLIP_DURATION", "15"))
    max_clip_duration: int = int(os.getenv("MAX_CLIP_DURATION", "90"))

    # Output
    default_format: str = os.getenv("DEFAULT_FORMAT", "vertical")

    # Paths
    output_dir: Path = field(default_factory=lambda: OUTPUT_DIR)
    fonts_dir: Path = field(default_factory=lambda: FONTS_DIR)
    music_dir: Path = field(default_factory=lambda: MUSIC_DIR)

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def has_llm_key(self) -> bool:
        return bool(self.anthropic_api_key or self.openai_api_key)

    @property
    def llm_provider(self) -> str:
        # Explicit backend override wins
        if self.llm_backend == "ollama":
            return "ollama"
        if self.llm_backend == "anthropic" and self.anthropic_api_key:
            return "anthropic"
        if self.llm_backend == "openai" and self.openai_api_key:
            return "openai"
        # Auto-detect fallback
        if self.anthropic_api_key:
            return "anthropic"
        if self.openai_api_key:
            return "openai"
        return "ollama"  # default to local


FORMAT_PRESETS = {
    "vertical": {"width": 1080, "height": 1920, "label": "9:16 (Reels/TikTok)"},
    "square": {"width": 1080, "height": 1080, "label": "1:1 (Instagram)"},
    "horizontal": {"width": 1920, "height": 1080, "label": "16:9 (YouTube)"},
}

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".ogg", ".flac"}
SUPPORTED_FONT_EXTENSIONS = {".ttf", ".otf"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
