"""Audio transcription using faster-whisper."""

from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel

from .config import Config


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list = None

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class TranscriptionResult:
    segments: list[Segment]
    language: str
    language_probability: float

    @property
    def full_text(self) -> str:
        return " ".join(seg.text.strip() for seg in self.segments)

    @property
    def duration(self) -> float:
        if not self.segments:
            return 0.0
        return self.segments[-1].end

    def to_srt(self) -> str:
        lines = []
        for i, seg in enumerate(self.segments, 1):
            start_ts = _format_timestamp_srt(seg.start)
            end_ts = _format_timestamp_srt(seg.end)
            lines.append(f"{i}")
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(seg.text.strip())
            lines.append("")
        return "\n".join(lines)

    def save_srt(self, path: Path) -> Path:
        path.write_text(self.to_srt(), encoding="utf-8")
        return path


class Transcriber:
    def __init__(self, config: Config):
        self.config = config
        self._model: WhisperModel | None = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            print(f"[transcriber] Loading whisper model: {self.config.whisper_model}")
            self._model = WhisperModel(
                self.config.whisper_model,
                device="cpu",
                compute_type="int8",
            )
        return self._model

    def transcribe(self, video_path: Path) -> TranscriptionResult:
        model = self._get_model()
        language = None if self.config.default_language == "auto" else self.config.default_language

        print(f"[transcriber] Transcribing: {video_path.name}")
        segments_gen, info = model.transcribe(
            str(video_path),
            language=language,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        segments = []
        for seg in segments_gen:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append(Word(start=w.start, end=w.end, text=w.word))
            segments.append(Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text,
                words=words,
            ))

        lang = info.language
        prob = info.language_probability
        print(f"[transcriber] Detected language: {lang} ({prob:.0%})")
        print(f"[transcriber] Segments: {len(segments)}")

        return TranscriptionResult(
            segments=segments,
            language=lang,
            language_probability=prob,
        )


def _format_timestamp_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
