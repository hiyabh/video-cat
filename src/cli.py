"""Command-line interface for VideoCat."""

import argparse
import sys
from pathlib import Path

from .config import Config, FORMAT_PRESETS
from .pipeline import run_pipeline
from .video_processor import ProcessingOptions


def main():
    parser = argparse.ArgumentParser(
        prog="videocat",
        description="Turn long videos into short viral clips with auto-subtitles",
    )
    parser.add_argument("input", type=Path, help="Path to input video file")
    parser.add_argument(
        "-f", "--format",
        choices=list(FORMAT_PRESETS.keys()),
        default=None,
        help="Output format (default: from .env)",
    )
    parser.add_argument(
        "-n", "--max-clips",
        type=int,
        default=None,
        help="Max number of clips to generate",
    )
    parser.add_argument(
        "--min-duration",
        type=int,
        default=None,
        help="Minimum clip duration in seconds",
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        default=None,
        help="Maximum clip duration in seconds",
    )
    parser.add_argument(
        "-l", "--language",
        default=None,
        help="Language code (he, en, ar, etc.) or 'auto'",
    )
    parser.add_argument(
        "-m", "--model",
        default=None,
        help="Whisper model size (tiny, base, small, medium, large-v3)",
    )
    parser.add_argument(
        "--music",
        type=Path,
        default=None,
        help="Path to background music file",
    )
    parser.add_argument(
        "--logo",
        type=Path,
        default=None,
        help="Path to logo image (PNG)",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=None,
        help="Path to custom font file (TTF/OTF)",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=None,
        help="Subtitle font size (default: auto-scale by format)",
    )
    parser.add_argument(
        "--no-animate",
        action="store_true",
        help="Disable word-by-word subtitle animation",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output directory (default: ./output/<video_name>)",
    )

    args = parser.parse_args()

    # Build config with CLI overrides
    config = Config()
    if args.max_clips is not None:
        config.max_clips = args.max_clips
    if args.min_duration is not None:
        config.min_clip_duration = args.min_duration
    if args.max_duration is not None:
        config.max_clip_duration = args.max_duration
    if args.language is not None:
        config.default_language = args.language
    if args.model is not None:
        config.whisper_model = args.model
    if args.output is not None:
        config.output_dir = args.output

    # Build processing options
    options = ProcessingOptions(
        format=args.format or config.default_format,
        font_path=args.font,
        font_size=args.font_size,
        background_music=args.music,
        logo_path=args.logo,
        animate_words=not args.no_animate,
    )

    # Run
    print(f"VideoCat — Processing: {args.input.name}")
    print(f"Format: {FORMAT_PRESETS[options.format]['label']}")
    print(f"Max clips: {config.max_clips}")
    print("-" * 40)

    try:
        result = run_pipeline(args.input, config, options)
        print()
        print("=" * 40)
        print(f"Created {len(result.clips)} clips:")
        for clip_path in result.clips:
            print(f"  {clip_path}")
        print(f"SRT: {result.srt_path}")
        print(f"Output dir: {result.clips[0].parent if result.clips else 'N/A'}")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
