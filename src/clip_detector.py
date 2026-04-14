"""Detect interesting clip-worthy segments using LLM analysis."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .transcriber import TranscriptionResult


@dataclass
class ClipSuggestion:
    start: float
    end: float
    title: str
    reason: str

    @property
    def duration(self) -> float:
        return self.end - self.start


CLIP_DETECTION_PROMPT = """You are a viral video editor. Analyze this transcript and find the {max_clips} most engaging, viral-worthy segments.

Rules:
- Each clip should be {min_duration}-{max_duration} seconds long
- Look for: emotional moments, surprising statements, funny lines, strong opinions, key insights, quotable phrases
- Clips must start and end at natural sentence boundaries
- Prefer segments that work as standalone content (make sense without context)

Transcript (with timestamps in seconds):
{transcript}

Respond with ONLY a JSON array, no other text:
[
  {{
    "start": 12.5,
    "end": 45.2,
    "title": "short catchy title for this clip",
    "reason": "why this segment is engaging"
  }}
]"""


def detect_clips_with_llm(
    transcription: TranscriptionResult,
    config: Config,
) -> list[ClipSuggestion]:
    transcript_text = _format_transcript_for_llm(transcription)

    prompt = CLIP_DETECTION_PROMPT.format(
        max_clips=config.max_clips,
        min_duration=config.min_clip_duration,
        max_duration=config.max_clip_duration,
        transcript=transcript_text,
    )

    if config.llm_provider == "anthropic":
        raw = _call_anthropic(prompt, config.anthropic_api_key)
    elif config.llm_provider == "openai":
        raw = _call_openai(prompt, config.openai_api_key)
    else:
        print("[clip_detector] No LLM key found, using fallback uniform split")
        return detect_clips_uniform(transcription, config)

    return _parse_response(raw)


def detect_clips_uniform(
    transcription: TranscriptionResult,
    config: Config,
) -> list[ClipSuggestion]:
    """Fallback: split video into equal segments when no LLM is available."""
    total_duration = transcription.duration
    clip_duration = config.max_clip_duration
    clips = []

    current = 0.0
    idx = 0
    while current < total_duration and idx < config.max_clips:
        end = min(current + clip_duration, total_duration)
        end = _snap_to_segment_boundary(end, transcription)
        clips.append(ClipSuggestion(
            start=current,
            end=end,
            title=f"Clip {idx + 1}",
            reason="Uniform split (no LLM)",
        ))
        current = end
        idx += 1

    return clips


def _format_transcript_for_llm(transcription: TranscriptionResult) -> str:
    lines = []
    for seg in transcription.segments:
        lines.append(f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.text.strip()}")
    return "\n".join(lines)


def _call_anthropic(prompt: str, api_key: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    print("[clip_detector] Analyzing transcript with Claude...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _call_openai(prompt: str, api_key: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    print("[clip_detector] Analyzing transcript with GPT...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )
    return response.choices[0].message.content


def _parse_response(raw: str) -> list[ClipSuggestion]:
    json_match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not json_match:
        print(f"[clip_detector] Warning: Could not parse LLM response")
        return []

    data = json.loads(json_match.group())
    clips = []
    for item in data:
        clips.append(ClipSuggestion(
            start=float(item["start"]),
            end=float(item["end"]),
            title=item.get("title", "Untitled"),
            reason=item.get("reason", ""),
        ))
    return clips


def _snap_to_segment_boundary(
    timestamp: float,
    transcription: TranscriptionResult,
) -> float:
    """Snap a timestamp to the nearest segment end boundary."""
    closest = timestamp
    min_diff = float("inf")
    for seg in transcription.segments:
        diff = abs(seg.end - timestamp)
        if diff < min_diff:
            min_diff = diff
            closest = seg.end
    return closest
