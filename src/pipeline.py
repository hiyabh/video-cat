"""Main processing pipeline — orchestrates all steps."""

from dataclasses import dataclass
from pathlib import Path

from .config import Config, SUPPORTED_VIDEO_EXTENSIONS
from .transcriber import Transcriber, TranscriptionResult
from .clip_detector import detect_clips_with_llm, ClipSuggestion
from .video_processor import process_clip, ProcessingOptions


@dataclass
class PipelineResult:
    input_path: Path
    clips: list[Path]
    srt_path: Path
    suggestions: list[ClipSuggestion]
    transcription: TranscriptionResult


def run_pipeline(
    input_path: Path,
    config: Config,
    options: ProcessingOptions | None = None,
    progress_callback: callable = None,
) -> PipelineResult:
    """Full pipeline: transcribe → detect → process clips."""
    if options is None:
        options = ProcessingOptions(format=config.default_format)

    input_path = Path(input_path)
    _validate_input(input_path)

    # Create output directory for this video
    video_output_dir = config.output_dir / input_path.stem
    video_output_dir.mkdir(parents=True, exist_ok=True)

    def _report(step: str, pct: int):
        msg = f"[pipeline] [{pct}%] {step}"
        print(msg)
        if progress_callback:
            progress_callback(step, pct)

    # Step 1: Transcribe
    _report("Transcribing audio...", 10)
    transcriber = Transcriber(config)
    transcription = transcriber.transcribe(input_path)

    # Save SRT
    srt_path = video_output_dir / f"{input_path.stem}.srt"
    transcription.save_srt(srt_path)
    _report(f"Saved SRT: {srt_path.name}", 25)

    # Step 2: Detect interesting clips
    _report("Detecting interesting segments...", 30)
    suggestions = detect_clips_with_llm(transcription, config)
    _report(f"Found {len(suggestions)} clip candidates", 40)

    if not suggestions:
        print("[pipeline] No clips detected. Check transcript quality.")
        return PipelineResult(
            input_path=input_path,
            clips=[],
            srt_path=srt_path,
            suggestions=[],
            transcription=transcription,
        )

    # Step 3: Process each clip
    # Propagate detected language to options for proper RTL handling
    options.language = transcription.language

    output_clips = []
    for i, clip in enumerate(suggestions):
        pct = 40 + int((i / len(suggestions)) * 55)
        _report(f"Processing clip {i + 1}/{len(suggestions)}: {clip.title}", pct)

        clip_filename = f"clip_{i + 1:02d}_{_sanitize_filename(clip.title)}.mp4"
        clip_output = video_output_dir / clip_filename

        try:
            process_clip(input_path, clip_output, clip, transcription, options)
            output_clips.append(clip_output)
            _report(f"Saved: {clip_filename}", pct + 5)
        except Exception as e:
            print(f"[pipeline] Error processing clip {i + 1}: {e}")
            continue

    _report(f"Done! {len(output_clips)} clips created", 100)

    return PipelineResult(
        input_path=input_path,
        clips=output_clips,
        srt_path=srt_path,
        suggestions=suggestions,
        transcription=transcription,
    )


def _validate_input(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")
    if path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError(
            f"Unsupported format: {path.suffix}. "
            f"Supported: {', '.join(SUPPORTED_VIDEO_EXTENSIONS)}"
        )


def _sanitize_filename(name: str) -> str:
    """Create filesystem-safe filename from clip title."""
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in name)
    return safe.strip().replace(" ", "_")[:40]
