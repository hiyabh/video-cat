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


CLIP_DETECTION_PROMPT = """You are a viral video editor. Find the {max_clips} most engaging segments in this transcript.

Rules:
- Each clip: {min_duration}-{max_duration} seconds long
- Look for: emotional moments, surprising statements, funny lines, strong opinions, insights, quotable phrases
- Start/end at natural sentence boundaries
- Prefer segments that work standalone

Transcript:
{transcript}

IMPORTANT: Return a SINGLE JSON object with ONE "clips" array. No duplicates. Exact format:
{{"clips":[{{"start":12.5,"end":45.2,"title":"catchy title","reason":"why engaging"}}]}}"""


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

    try:
        if config.llm_provider == "anthropic":
            raw = _call_anthropic(prompt, config.anthropic_api_key)
        elif config.llm_provider == "openai":
            raw = _call_openai(prompt, config.openai_api_key)
        elif config.llm_provider == "ollama":
            raw = _call_ollama(prompt, config.ollama_model, config.ollama_host)
        else:
            print("[clip_detector] No LLM configured, using fallback uniform split")
            return detect_clips_uniform(transcription, config)
    except Exception as e:
        print(f"[clip_detector] LLM error: {e}. Using fallback uniform split.")
        return detect_clips_uniform(transcription, config)

    clips = _parse_response(raw)
    return _validate_clips(clips, transcription, config)


def _validate_clips(
    clips: list[ClipSuggestion],
    transcription: TranscriptionResult,
    config: Config,
) -> list[ClipSuggestion]:
    """Enforce duration constraints — extend short clips, drop impossible ones."""
    total = transcription.duration
    valid = []
    for clip in clips:
        # Clamp to video bounds
        start = max(0.0, min(clip.start, total))
        end = max(0.0, min(clip.end, total))

        duration = end - start
        if duration < config.min_clip_duration:
            # Extend end to reach minimum
            needed = config.min_clip_duration - duration
            end = min(total, end + needed)
            # If still too short, also pull start back
            if end - start < config.min_clip_duration:
                start = max(0.0, start - (config.min_clip_duration - (end - start)))

            # Snap to segment boundary for natural cut
            end = _snap_to_segment_boundary(end, transcription)

            duration = end - start
            if duration < config.min_clip_duration * 0.7:
                print(f"[clip_detector] Skipping too-short clip: {clip.title} ({duration:.1f}s)")
                continue
            print(f"[clip_detector] Extended short clip: {clip.title} -> {duration:.1f}s")

        # Cap max duration
        if duration > config.max_clip_duration:
            end = start + config.max_clip_duration
            end = _snap_to_segment_boundary(end, transcription)

        valid.append(ClipSuggestion(
            start=start, end=end, title=clip.title, reason=clip.reason,
        ))
    return valid


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


def _call_ollama(prompt: str, model: str, host: str) -> str:
    import urllib.request
    import urllib.error

    print(f"[clip_detector] Analyzing transcript with Ollama ({model})...")
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "top_p": 0.9, "num_ctx": 8192},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{host}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "")
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach Ollama at {host}. Is it running? "
            f"Start with: ollama serve. Original: {e}"
        )


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
    # Try direct JSON parse (Ollama format=json)
    data = None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            data = parsed
        elif isinstance(parsed, dict):
            # Some models wrap in {"clips": [...]}
            for key in ("clips", "segments", "results", "data"):
                if key in parsed and isinstance(parsed[key], list):
                    data = parsed[key]
                    break
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: extract JSON array from text
    if data is None:
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not json_match:
            print("[clip_detector] Warning: Could not parse LLM response")
            return []
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            print(f"[clip_detector] JSON parse error: {e}")
            return []

    clips = []
    for item in data:
        try:
            clips.append(ClipSuggestion(
                start=float(item["start"]),
                end=float(item["end"]),
                title=item.get("title", "Untitled"),
                reason=item.get("reason", ""),
            ))
        except (KeyError, ValueError, TypeError) as e:
            print(f"[clip_detector] Skipping malformed clip: {e}")
            continue
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
