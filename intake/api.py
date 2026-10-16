"""Stable application interface for the Streamlit UI and Promptfoo provider."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .examples import examples
from .parser import parse_transcript
from .provider import ProviderError, request_extraction
from .render import render_handoff
from .schema import OutputValidationError, validate_extraction
from .settings import Settings, get_settings
from .validation import validate_vehicle


def list_examples() -> list[dict[str, Any]]:
    """Return isolated copies of the six synthetic review examples."""
    return deepcopy(examples)


def process_intake(
    transcript: str,
    vehicle: dict[str, str],
    *,
    saved_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process saved or live extraction through the same validation and renderer."""
    settings = get_settings()
    source = "saved" if saved_result is not None else "live"
    errors: list[str] = []

    try:
        turns = parse_transcript(transcript)
    except ValueError as exc:
        return _invalid_result(source, settings, str(exc))

    try:
        normalized_vehicle = validate_vehicle(vehicle)
    except ValueError as exc:
        return _invalid_result(source, settings, str(exc))

    if saved_result is not None:
        candidate: object = saved_result
    else:
        if settings.configuration_error:
            return _invalid_result(source, settings, settings.configuration_error)
        if not settings.configured:
            return _invalid_result(
                source,
                settings,
                "Live processing is unavailable. Set INTAKE_API_KEY on the server to run a fresh model request.",
            )
        try:
            candidate = request_extraction(
                transcript=transcript,
                turns=turns,
                vehicle=normalized_vehicle,
                settings=settings,
            )
        except (ProviderError, OutputValidationError) as exc:
            return _invalid_result(source, settings, str(exc))

    try:
        extraction = validate_extraction(candidate, turns, normalized_vehicle)
    except OutputValidationError as exc:
        return _invalid_result(source, settings, str(exc))

    return {
        "source": source,
        "facts": [
            {
                "id": fact.id,
                "field": fact.field,
                "label": _label(fact.field),
                "value": fact.value,
                "evidence": [item.model_dump(mode="json") for item in fact.evidence],
            }
            for fact in extraction.facts
        ],
        "corrections": [
            {
                "field": correction.field,
                "previous_value": correction.previous_value,
                "current_value": correction.current_value,
                "evidence": [item.model_dump(mode="json") for item in correction.evidence],
            }
            for correction in extraction.corrections
        ],
        "conflicts": [
            {
                "field": conflict.field,
                "values": list(conflict.values),
                "evidence": [item.model_dump(mode="json") for item in conflict.evidence],
            }
            for conflict in extraction.conflicts
        ],
        "questions": list(extraction.questions),
        "handoff": render_handoff(extraction, normalized_vehicle),
        "errors": errors,
        "valid": True,
        "model": settings.model,
    }


def _label(field: str) -> str:
    from .schema import FIELD_LABELS

    return FIELD_LABELS[field]


def _invalid_result(source: str, settings: Settings, error: str) -> dict[str, Any]:
    return {
        "source": source,
        "facts": [],
        "corrections": [],
        "conflicts": [],
        "questions": [],
        "handoff": "",
        "errors": [error],
        "valid": False,
        "model": settings.model,
    }
