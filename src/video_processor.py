"""Video processing with FFmpeg — cutting, subtitles, format, overlays."""

import os
import subprocess
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import Config, FORMAT_PRESETS
from .clip_detector import ClipSuggestion
from .transcriber import TranscriptionResult, Segment, Word


RTL_LANGS = {"he", "ar", "fa", "ur", "yi", "iw"}
WORDS_PER_SUBTITLE = 5
MAX_SUBTITLE_DURATION = 3.0


def _find_binary(name: str) -> str:
    """Find binary: prefer bundled (PyInstaller _internal), then PATH."""
    # PyInstaller frozen: check _MEIPASS and sys.executable dir
    if getattr(sys, "frozen", False):
        for base in (Path(sys._MEIPASS), Path(sys.executable).parent, Path(sys.executable).parent / "_internal"):
            candidate = base / f"{name}.exe"
            if candidate.exists():
                return str(candidate)
    # Dev mode: PATH
    found = shutil.which(name)
    return found if found else name


FFMPEG = _find_binary("ffmpeg")
FFPROBE = _find_binary("ffprobe")


@dataclass
class ProcessingOptions:
    format: str = "vertical"
    subtitle_style: str = "modern"
    font_path: Path | None = None
    font_size: int | None = None  # auto-scale by format if None
    font_color: str = "&H00FFFFFF"
    outline_color: str = "&H00000000"
    outline_width: int = 4
    background_music: Path | None = None
    music_volume: float = 0.15
    logo_path: Path | None = None
    logo_position: str = "top_right"
    logo_scale: float = 0.12
    animate_words: bool = True
    language: str = "auto"  # set from transcription for RTL detection

    def get_font_size(self) -> int:
        if self.font_size:
            return self.font_size
        # Viral-style large subtitles (~8-10% of screen height)
        if self.format == "vertical":
            return 140  # 1920 * 0.073
        elif self.format == "square":
            return 110
        return 90  # horizontal


def cut_clip(
    input_path: Path,
    output_path: Path,
    start: float,
    end: float,
) -> Path:
    """Cut a segment from video without re-encoding (fast)."""
    duration = end - start
    cmd = [
        FFMPEG, "-y",
        "-ss", str(start),
        "-i", str(input_path),
        "-t", str(duration),
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]
    _run_ffmpeg(cmd, f"Cutting {start:.1f}s - {end:.1f}s")
    return output_path


def get_video_info(input_path: Path) -> dict:
    """Get video dimensions and duration."""
    cmd = [
        FFPROBE,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(input_path),
    ]
    import json
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    video_stream = next(
        (s for s in data.get("streams", []) if s["codec_type"] == "video"),
        None,
    )
    if not video_stream:
        raise ValueError(f"No video stream found in {input_path}")

    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "duration": float(data["format"].get("duration", 0)),
    }


def process_clip(
    input_path: Path,
    output_path: Path,
    clip: ClipSuggestion,
    transcription: TranscriptionResult,
    options: ProcessingOptions,
) -> Path:
    """Full processing pipeline: cut → subtitle → reformat → overlays."""
    temp_dir = output_path.parent / "_temp"
    temp_dir.mkdir(exist_ok=True)

    try:
        # Step 1: Cut the clip segment
        cut_path = temp_dir / "cut.mp4"
        _cut_with_reencode(input_path, cut_path, clip.start, clip.end)

        # Step 2: Generate subtitle file for this clip
        clip_segments = _get_segments_for_clip(transcription, clip)
        ass_path = temp_dir / "subs.ass"
        _generate_ass_subtitles(clip_segments, ass_path, clip.start, options)

        # Step 3: Apply subtitles + reformat
        formatted_path = temp_dir / "formatted.mp4"
        _apply_subtitles_and_format(cut_path, formatted_path, ass_path, options)

        # Step 4: Add background music (optional)
        if options.background_music and options.background_music.exists():
            music_path = temp_dir / "with_music.mp4"
            _add_background_music(formatted_path, music_path, options)
            formatted_path = music_path

        # Step 5: Add logo (optional)
        if options.logo_path and options.logo_path.exists():
            logo_out = temp_dir / "with_logo.mp4"
            _add_logo_overlay(formatted_path, logo_out, options)
            formatted_path = logo_out

        # Move final to output
        shutil.move(str(formatted_path), str(output_path))
        return output_path

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _cut_with_reencode(
    input_path: Path, output_path: Path, start: float, end: float,
) -> None:
    """Cut with re-encoding for precise timestamps."""
    duration = end - start
    cmd = [
        FFMPEG, "-y",
        "-ss", str(start),
        "-i", str(input_path),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "Cutting clip")


def _get_segments_for_clip(
    transcription: TranscriptionResult,
    clip: ClipSuggestion,
) -> list[Segment]:
    """Extract and re-chunk transcription into small subtitle-friendly segments."""
    # Collect all words within the clip range
    words_in_clip = []
    for seg in transcription.segments:
        if seg.end <= clip.start or seg.start >= clip.end:
            continue
        if seg.words:
            for w in seg.words:
                if w.end > clip.start and w.start < clip.end:
                    words_in_clip.append(Word(
                        start=max(0, w.start - clip.start),
                        end=w.end - clip.start,
                        text=w.text,
                    ))
        else:
            # Fallback — no word timestamps, use segment as one chunk
            words_in_clip.append(Word(
                start=max(0, seg.start - clip.start),
                end=seg.end - clip.start,
                text=seg.text,
            ))

    # Group words into small chunks (N words or max duration)
    chunks = []
    current = []
    for w in words_in_clip:
        if not current:
            current.append(w)
            continue
        chunk_start = current[0].start
        chunk_duration = w.end - chunk_start
        if len(current) >= WORDS_PER_SUBTITLE or chunk_duration >= MAX_SUBTITLE_DURATION:
            chunks.append(current)
            current = [w]
        else:
            current.append(w)
    if current:
        chunks.append(current)

    # Build Segment per chunk
    segments = []
    for chunk in chunks:
        text = "".join(w.text for w in chunk).strip()
        segments.append(Segment(
            start=chunk[0].start,
            end=chunk[-1].end,
            text=text,
            words=chunk,
        ))
    return segments


def _generate_ass_subtitles(
    segments: list[Segment],
    output_path: Path,
    time_offset: float,
    options: ProcessingOptions,
) -> None:
    """Generate ASS subtitle file with styling and word-by-word animation."""
    fmt = FORMAT_PRESETS.get(options.format, FORMAT_PRESETS["vertical"])
    play_res_x = fmt["width"]
    play_res_y = fmt["height"]
    margin_v = int(play_res_y * 0.10)
    font_size = options.get_font_size()

    font_name = "Arial"
    if options.font_path and options.font_path.exists():
        font_name = options.font_path.stem

    is_rtl = options.language in RTL_LANGS

    header = f"""[Script Info]
Title: VideoCat Subtitles
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{options.font_color},&H000000FF,{options.outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,{options.outline_width * 2},3,2,60,60,{margin_v},0
Style: Highlight,{font_name},{font_size},&H0000FFFF,&H000000FF,{options.outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,{options.outline_width * 2},3,2,60,60,{margin_v},0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for seg in segments:
        start_ts = _format_ass_timestamp(seg.start)
        end_ts = _format_ass_timestamp(seg.end)
        text = seg.text.strip()

        # libass handles BiDi natively via fribidi — pass logical order text as-is
        if options.animate_words and seg.words and len(seg.words) > 1 and not is_rtl:
            # Karaoke animation works poorly with RTL — use plain text for Hebrew/Arabic
            animated = _animate_words_karaoke_wtimes(seg.words, seg.start)
            events.append(
                f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{animated}"
            )
        else:
            events.append(
                f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
            )

    output_path.write_text(header + "\n".join(events), encoding="utf-8-sig")


def _apply_bidi(text: str) -> str:
    """Apply BiDi algorithm to get visual-order text for RTL languages."""
    try:
        from bidi.algorithm import get_display
        return get_display(text)
    except ImportError:
        return text


def _animate_words_karaoke_wtimes(words: list, chunk_start: float) -> str:
    """Build karaoke timing from actual word timestamps."""
    parts = []
    prev_end = chunk_start
    for w in words:
        # Gap before this word (silence)
        gap_cs = max(0, int((w.start - prev_end) * 100))
        if gap_cs > 0:
            parts.append(f"{{\\k{gap_cs}}}")
        duration_cs = max(1, int((w.end - w.start) * 100))
        parts.append(f"{{\\kf{duration_cs}}}{w.text}")
        prev_end = w.end
    return "".join(parts).strip()


def _animate_words_karaoke(text: str, start: float, end: float) -> str:
    """Create word-by-word highlight animation using ASS override tags."""
    words = text.split()
    if not words:
        return text

    total_duration = end - start
    duration_per_word_cs = int((total_duration / len(words)) * 100)

    parts = []
    for word in words:
        parts.append(f"{{\\kf{duration_per_word_cs}}}{word}")

    return " ".join(parts)


def _apply_subtitles_and_format(
    input_path: Path,
    output_path: Path,
    ass_path: Path,
    options: ProcessingOptions,
) -> None:
    """Burn subtitles and reformat to target aspect ratio."""
    fmt = FORMAT_PRESETS.get(options.format, FORMAT_PRESETS["vertical"])
    w, h = fmt["width"], fmt["height"]

    # Build filter: scale/crop to target format, then burn subtitles
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")
    fonts_dir = ""
    if options.font_path and options.font_path.exists():
        fonts_dir_path = options.font_path.parent
        fonts_dir = f":fontsdir={str(fonts_dir_path).replace(chr(92), '/').replace(':', chr(92) + ':')}"

    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"ass='{ass_escaped}'{fonts_dir}"
    )

    cmd = [
        FFMPEG, "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]
    _run_ffmpeg(cmd, f"Formatting to {options.format} with subtitles")


def _add_background_music(
    input_path: Path,
    output_path: Path,
    options: ProcessingOptions,
) -> None:
    """Mix background music at specified volume."""
    cmd = [
        FFMPEG, "-y",
        "-i", str(input_path),
        "-i", str(options.background_music),
        "-filter_complex",
        f"[1:a]volume={options.music_volume}[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[out]",
        "-map", "0:v", "-map", "[out]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "Adding background music")


def _add_logo_overlay(
    input_path: Path,
    output_path: Path,
    options: ProcessingOptions,
) -> None:
    """Overlay a logo image on the video."""
    info = get_video_info(input_path)
    logo_w = int(info["width"] * options.logo_scale)

    position_map = {
        "top_right": f"W-w-20:20",
        "top_left": "20:20",
        "bottom_right": f"W-w-20:H-h-20",
        "bottom_left": "20:H-h-20",
    }
    pos = position_map.get(options.logo_position, position_map["top_right"])

    cmd = [
        FFMPEG, "-y",
        "-i", str(input_path),
        "-i", str(options.logo_path),
        "-filter_complex",
        f"[1:v]scale={logo_w}:-1[logo];[0:v][logo]overlay={pos}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "Adding logo overlay")


def _format_ass_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _run_ffmpeg(cmd: list[str], description: str) -> None:
    print(f"[ffmpeg] {description}...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        error_lines = result.stderr.strip().split("\n")[-5:]
        raise RuntimeError(
            f"FFmpeg failed: {description}\n" + "\n".join(error_lines)
        )
