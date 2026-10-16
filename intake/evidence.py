"""Exact, boundary-aware matching between reported values and transcript quotes."""

from __future__ import annotations

import re


def value_spans_in_text(field: str, value: str, text: str) -> list[tuple[int, int]]:
    """Return exact value spans, avoiding partial numeric or identifier tokens."""
    if not value:
        return []
    escaped = re.escape(value)
    if field in {"mileage", "year"}:
        pattern = re.compile(rf"(?<![0-9,]){escaped}(?![0-9,])")
        return [(match.start(), match.end()) for match in pattern.finditer(text)]
    if field == "vin":
        pattern = re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])")
        return [(match.start(), match.end()) for match in pattern.finditer(text)]

    spans: list[tuple[int, int]] = []
    start = 0
    while (index := text.find(value, start)) >= 0:
        spans.append((index, index + len(value)))
        start = index + 1
    return spans


def value_matches_quote(field: str, value: str, quote: str) -> bool:
    return bool(value_spans_in_text(field, value, quote))
