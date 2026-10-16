"""Deterministic plain-text write-up rendering."""

from __future__ import annotations

from .evidence import value_matches_quote
from .schema import Evidence, Extraction, FIELD_LABELS


def render_handoff(extraction: Extraction, vehicle: dict[str, str] | None = None) -> str:
    """Render only validated, attributed source snippets and follow-up questions."""
    lines = ["SERVICE INTAKE DRAFT"]
    if extraction.facts:
        lines.extend(["", "Reported details:"])
        for fact in extraction.facts:
            evidence = _evidence_for(fact.field, fact.value, fact.evidence)
            lines.append(
                f'- {FIELD_LABELS[fact.field]}: "{fact.value}" '
                f"({_ref(evidence)})"
            )
    if extraction.corrections:
        lines.extend(["", "Correction history:"])
        for correction in extraction.corrections:
            previous = _evidence_for(correction.field, correction.previous_value, correction.evidence)
            current = _evidence_for(correction.field, correction.current_value, correction.evidence)
            lines.append(
                f'- {FIELD_LABELS[correction.field]} changed from "{correction.previous_value}" '
                f"({_ref(previous)}) to "
                f'"{correction.current_value}" ({_ref(current)})'
            )
    if extraction.conflicts:
        lines.extend(["", "Unresolved conflicts:"])
        for conflict in extraction.conflicts:
            sources = []
            for value in conflict.values:
                source = _evidence_for(conflict.field, value, conflict.evidence)
                sources.append(f'"{value}" ({_ref(source)})')
            lines.append(f"- {FIELD_LABELS[conflict.field]}: " + "; ".join(sources))
    if extraction.questions:
        lines.extend(["", "Open questions:"])
        lines.extend(f"- {question}" for question in extraction.questions)
    if vehicle:
        labels = {
            "vin": "VIN",
            "model": "Vehicle model",
            "year": "Vehicle year",
            "mileage": "Vehicle mileage",
        }
        lines.extend(["", "Supplied vehicle context:"])
        lines.extend(f"- {labels[field]}: {value}" for field, value in vehicle.items())
    if not extraction.facts and not extraction.corrections and not extraction.conflicts:
        lines.extend(["", "No reported details were extracted."])
    return "\n".join(lines)


def _evidence_for(field: str, value: str, evidence: list[Evidence]) -> Evidence:
    return next(item for item in evidence if value_matches_quote(field, value, item.quote))


def _ref(item: Evidence) -> str:
    """Turn ids are sequential, so T3 prints as line 3."""
    return f"{item.speaker}, line {item.turn_id[1:]}"
