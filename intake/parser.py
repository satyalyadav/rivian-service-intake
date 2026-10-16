"""Transcript parsing for one physical line per speaker turn."""

from __future__ import annotations

import re


MAX_TRANSCRIPT_CHARS = 12_000
MAX_TURNS = 100
MAX_SPEAKER_CHARS = 40
_TURN_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 _'-]{0,39}): (.*)$")


def parse_transcript(text: str) -> list[dict[str, str]]:
    """Parse `Speaker: text` lines and preserve text after the separator."""
    if not isinstance(text, str):
        raise ValueError("Transcript must be text.")
    if len(text) > MAX_TRANSCRIPT_CHARS:
        raise ValueError(f"Transcript exceeds the {MAX_TRANSCRIPT_CHARS:,} character limit.")

    turns: list[dict[str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        match = _TURN_RE.fullmatch(line)
        if not match:
            raise ValueError(
                f"Line {line_number} must use the format 'Speaker: text' with a valid speaker name."
            )
        speaker, turn_text = match.groups()
        if len(speaker) > MAX_SPEAKER_CHARS:
            raise ValueError(f"Speaker on line {line_number} is too long.")
        turns.append({"id": f"T{len(turns) + 1}", "speaker": speaker, "text": turn_text})
        if len(turns) > MAX_TURNS:
            raise ValueError(f"Transcript exceeds the {MAX_TURNS} turn limit.")
    if not turns:
        raise ValueError("Add at least one conversation turn.")
    return turns
