"""Small helpers for safely displaying quoted transcript evidence."""

from __future__ import annotations

import html


def highlighted_text_html(text: str, quotes: list[str]) -> str:
    """Escape transcript text and mark the merged raw-text quote spans."""
    spans: list[tuple[int, int]] = []
    for quote in quotes:
        if not quote:
            continue
        start = 0
        while (index := text.find(quote, start)) >= 0:
            spans.append((index, index + len(quote)))
            start = index + 1

    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    parts: list[str] = []
    cursor = 0
    for start, end in merged:
        parts.append(html.escape(text[cursor:start]))
        parts.append('<mark class="ev">' + html.escape(text[start:end]) + "</mark>")
        cursor = end
    parts.append(html.escape(text[cursor:]))
    return "".join(parts)
