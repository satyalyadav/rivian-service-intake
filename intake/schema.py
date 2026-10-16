"""Strict structured output models and cross-reference validation."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated, Literal
import re

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from .evidence import value_matches_quote, value_spans_in_text
AllowedField = Literal[
    "concern",
    "mileage",
    "model",
    "year",
    "vin",
    "warning",
    "noise",
    "location",
    "timing",
    "frequency",
    "conditions",
    "service_history",
    "other_detail",
]

FIELD_LABELS: dict[str, str] = {
    "concern": "Concern",
    "mileage": "Mileage",
    "model": "Model",
    "year": "Year",
    "vin": "VIN",
    "warning": "Warning",
    "noise": "Noise",
    "location": "Location",
    "timing": "Timing",
    "frequency": "Frequency",
    "conditions": "Conditions",
    "service_history": "Service history",
    "other_detail": "Other detail",
}
SINGLE_VALUE_FIELDS = {"mileage", "model", "year", "vin"}

ShortValue = Annotated[str, StringConstraints(min_length=1, max_length=240, strict=True)]
Quote = Annotated[str, StringConstraints(min_length=1, max_length=600, strict=True)]
Speaker = Annotated[str, StringConstraints(min_length=1, max_length=40, strict=True)]
TurnId = Annotated[str, StringConstraints(pattern=r"^T[1-9][0-9]{0,2}$", strict=True)]
Question = Annotated[str, StringConstraints(min_length=4, max_length=240, strict=True)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Evidence(StrictModel):
    turn_id: TurnId
    speaker: Speaker
    quote: Quote


class FactCandidate(StrictModel):
    id: Annotated[str, StringConstraints(pattern=r"^F[1-9][0-9]{0,2}$", strict=True)]
    field: AllowedField
    value: ShortValue
    evidence: Annotated[list[Evidence], Field(min_length=1, max_length=5)]


class CorrectionCandidate(StrictModel):
    field: AllowedField
    previous_value: ShortValue
    current_value: ShortValue
    evidence: Annotated[list[Evidence], Field(min_length=2, max_length=6)]


class ConflictCandidate(StrictModel):
    field: AllowedField
    values: Annotated[list[ShortValue], Field(min_length=2, max_length=5)]
    evidence: Annotated[list[Evidence], Field(min_length=2, max_length=8)]


class Extraction(StrictModel):
    facts: Annotated[list[FactCandidate], Field(max_length=30)]
    corrections: Annotated[list[CorrectionCandidate], Field(max_length=10)]
    conflicts: Annotated[list[ConflictCandidate], Field(max_length=10)]
    questions: Annotated[list[Question], Field(max_length=3)]


class OutputValidationError(ValueError):
    """Safe, user-facing validation failure with no raw model output attached."""


def validate_extraction(
    candidate: object,
    turns: list[dict[str, str]],
    vehicle: dict[str, str],
) -> Extraction:
    try:
        extraction = Extraction.model_validate(candidate)
    except ValidationError as exc:
        raise OutputValidationError(
            "The model response did not match the required structured format. No write-up was generated."
        ) from exc

    expected_fact_ids = [f"F{index}" for index in range(1, len(extraction.facts) + 1)]
    if [fact.id for fact in extraction.facts] != expected_fact_ids:
        raise OutputValidationError("Fact identifiers were incomplete or repeated. No write-up was generated.")

    turn_index = {turn["id"]: turn for turn in turns}

    def check_evidence(items: list[Evidence], *, owner: str) -> list[Evidence]:
        checked: list[Evidence] = []
        seen: set[tuple[str, str, str]] = set()
        for item in items:
            turn = turn_index.get(item.turn_id)
            if turn is None or item.speaker != turn["speaker"] or item.quote not in turn["text"]:
                raise OutputValidationError(
                    f"Evidence for {owner} must quote the named speaker and turn exactly. No write-up was generated."
                )
            ref = (item.turn_id, item.speaker, item.quote)
            if ref not in seen:
                seen.add(ref)
                checked.append(item)
        return checked

    fact_fields: dict[str, list[FactCandidate]] = defaultdict(list)
    for fact in extraction.facts:
        evidence = check_evidence(fact.evidence, owner=fact.id)
        if not any(value_matches_quote(fact.field, fact.value, item.quote) for item in evidence):
            raise OutputValidationError(
                f"Evidence for {fact.id} does not contain its reported value. No write-up was generated."
            )
        fact_fields[fact.field].append(fact)

    correction_fields: dict[str, list[CorrectionCandidate]] = defaultdict(list)
    for correction in extraction.corrections:
        evidence = check_evidence(correction.evidence, owner=correction.field)
        if correction.previous_value == correction.current_value:
            raise OutputValidationError("A correction must change the reported value. No write-up was generated.")
        references = {(item.turn_id, item.speaker, item.quote) for item in evidence}
        if len(references) < 2:
            raise OutputValidationError(
                "A correction must preserve both source statements. No write-up was generated."
            )
        if not any(
            value_matches_quote(correction.field, correction.previous_value, item.quote)
            for item in evidence
        ) or not any(
            value_matches_quote(correction.field, correction.current_value, item.quote)
            for item in evidence
        ):
            raise OutputValidationError(
                "A correction must quote both the previous and current values. No write-up was generated."
            )
        previous_positions = _value_source_positions(
            correction.field, correction.previous_value, evidence, turns
        )
        current_positions = _value_source_positions(
            correction.field, correction.current_value, evidence, turns
        )
        if min(previous_positions) >= max(current_positions):
            raise OutputValidationError(
                "Correction history is out of order. No write-up was generated."
            )
        correction_fields[correction.field].append(correction)

    conflict_fields: dict[str, ConflictCandidate] = {}
    for conflict in extraction.conflicts:
        if conflict.field in conflict_fields:
            raise OutputValidationError("A field has repeated unresolved conflicts. No write-up was generated.")
        evidence = check_evidence(conflict.evidence, owner=conflict.field)
        unique_values = set(conflict.values)
        references = {(item.turn_id, item.speaker, item.quote) for item in evidence}
        if len(unique_values) != len(conflict.values) or len(references) < 2:
            raise OutputValidationError(
                "A conflict must preserve distinct values and at least two source statements. No write-up was generated."
            )
        if any(
            not any(value_matches_quote(conflict.field, value, item.quote) for item in evidence)
            for value in conflict.values
        ):
            raise OutputValidationError(
                "Evidence for a conflict must contain each reported value. No write-up was generated."
            )
        conflict_fields[conflict.field] = conflict

    if set(correction_fields) & set(conflict_fields):
        raise OutputValidationError(
            "A field cannot be both corrected and unresolved. No write-up was generated."
        )
    if set(fact_fields) & set(conflict_fields):
        raise OutputValidationError(
            "An unresolved field cannot also have a resolved fact. No write-up was generated."
        )

    for field, corrections in correction_fields.items():
        for previous, current in zip(corrections, corrections[1:]):
            if previous.current_value != current.previous_value:
                raise OutputValidationError(
                    "Correction history is out of order. No write-up was generated."
                )
        facts = fact_fields.get(field, [])
        if not facts or any(fact.value != corrections[-1].current_value for fact in facts):
            raise OutputValidationError(
                "The current fact does not match the last correction. No write-up was generated."
            )

    for field, facts in fact_fields.items():
        values = {fact.value for fact in facts}
        if len(values) > 1 and field in SINGLE_VALUE_FIELDS and field not in correction_fields:
            raise OutputValidationError(
                "Disagreeing values must remain unresolved as a conflict. No write-up was generated."
            )

    filtered_questions = _remove_questions_answered_by_vehicle(extraction.questions, vehicle)
    return extraction.model_copy(update={"questions": filtered_questions})


def _remove_questions_answered_by_vehicle(
    questions: list[str], vehicle: dict[str, str]
) -> list[str]:
    question_fields = {
        "vin": (r"\bvin\b", r"\bvehicle identification number\b"),
        "model": (r"\bmodel\b", r"\bvehicle model\b"),
        "year": (r"\byear\b", r"\bmodel year\b"),
        "mileage": (r"\bmileage\b", r"\bodometer\b"),
    }
    known = {field for field, value in vehicle.items() if value}
    filtered: list[str] = []
    for question in questions:
        question_lower = question.casefold()
        already_known = any(
            field in known and any(re.search(phrase, question_lower) for phrase in phrases)
            for field, phrases in question_fields.items()
        )
        if not already_known:
            filtered.append(question)
    return filtered


def _value_source_positions(
    field: str,
    value: str,
    evidence: list[Evidence],
    turns: list[dict[str, str]],
) -> set[tuple[int, int]]:
    """Locate evidence spans in transcript order when their positions are unambiguous."""
    turn_order = {turn["id"]: index for index, turn in enumerate(turns)}
    turn_text = {turn["id"]: turn["text"] for turn in turns}
    positions: set[tuple[int, int]] = set()
    for item in evidence:
        text = turn_text[item.turn_id]
        quote_starts: list[int] = []
        start = 0
        while (index := text.find(item.quote, start)) >= 0:
            quote_starts.append(index)
            start = index + 1
        value_spans = value_spans_in_text(field, value, item.quote)
        positions.update(
            (turn_order[item.turn_id], quote_start + value_start)
            for quote_start in quote_starts
            for value_start, _ in value_spans
        )
    return positions
