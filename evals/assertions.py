"""Promptfoo checks for the six predeclared intake expectations."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.cases import get_case


def _mileage_number(value: str) -> int | None:
    match = re.fullmatch(r"\s*([0-9][0-9,]*)(?:\s*(?:miles?|mi))?\s*", value, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _same_value(field: str, actual: str, expected: str) -> bool:
    if field == "mileage":
        actual_number = _mileage_number(actual)
        expected_number = _mileage_number(expected)
        if actual_number is not None and expected_number is not None:
            return actual_number == expected_number
    return actual == expected


def _required_fact_matches(field: str, actual: str, expected: str) -> bool:
    if not isinstance(actual, str):
        return False
    if field == "mileage":
        return _same_value(field, actual, expected)
    return expected.casefold() in actual.casefold()


def _same_conflict(field: str, actual: list[str], expected: list[str]) -> bool:
    if field == "mileage":
        actual_numbers = [_mileage_number(value) for value in actual]
        expected_numbers = [_mileage_number(value) for value in expected]
        return (
            None not in actual_numbers
            and None not in expected_numbers
            and sorted(actual_numbers) == sorted(expected_numbers)
        )
    return set(actual) == set(expected)


def get_assert(output: str, context: dict[str, Any]) -> dict[str, Any]:
    case_id = context.get("vars", {}).get("case_id")
    try:
        result = json.loads(output)
        case = get_case(case_id)
    except (TypeError, json.JSONDecodeError, KeyError):
        return {"pass": False, "score": 0, "reason": "Could not parse the pipeline output or case."}

    reasons: list[str] = []
    mode = os.getenv("INTAKE_EVAL_MODE", "saved").strip().casefold()
    expected_source = "saved" if mode == "saved" else "live"
    if not result.get("valid") or result.get("errors"):
        reasons.append("The pipeline returned invalid output.")
    if result.get("source") != expected_source:
        reasons.append(f"Expected source={expected_source}.")
    if not result.get("handoff"):
        reasons.append("No draft handoff was rendered.")

    facts = result.get("facts", [])
    for required in case["expect"].get("required_facts", []):
        if not any(
            fact.get("field") == required["field"]
            and _required_fact_matches(
                required["field"], fact.get("value", ""), required["value"]
            )
            for fact in facts
        ):
            reasons.append(f"Missing expected {required['field']} fact.")
    for alternative in case["expect"].get("fact_alternatives", []):
        fields = set(alternative["fields"])
        value_part = alternative["value_contains"].casefold()
        if not any(
            fact.get("field") in fields
            and value_part in fact.get("value", "").casefold()
            for fact in facts
        ):
            reasons.append(
                f"Missing a supported fact in {', '.join(sorted(fields))} containing '{value_part}'."
            )
    if len(result.get("corrections", [])) != case["expect"].get("corrections", len(result.get("corrections", []))):
        reasons.append("Correction count did not match the expectation.")
    expected_conflict_count = case["expect"].get("conflict_count")
    if expected_conflict_count is not None and len(result.get("conflicts", [])) != expected_conflict_count:
        reasons.append("Conflict count did not match the expectation.")

    expected_correction = case["expect"].get("correction")
    if expected_correction and not any(
        item.get("field") == expected_correction["field"]
        and _same_value(
            expected_correction["field"],
            item.get("previous_value", ""),
            expected_correction["previous_value"],
        )
        and _same_value(
            expected_correction["field"],
            item.get("current_value", ""),
            expected_correction["current_value"],
        )
        for item in result.get("corrections", [])
    ):
        reasons.append("The explicit correction history was not preserved.")

    for expected_conflict in case["expect"].get("conflicts", []):
        if not any(
            item.get("field") == expected_conflict["field"]
            and _same_conflict(
                expected_conflict["field"],
                item.get("values", []),
                expected_conflict["values"],
            )
            for item in result.get("conflicts", [])
        ):
            reasons.append("The unresolved values were not preserved as a conflict.")
    if set(case["expect"].get("no_fact_fields", [])) & {fact.get("field") for fact in facts}:
        reasons.append("A conflicted field was presented as resolved.")

    questions = result.get("questions", [])
    if len(questions) < case["expect"].get("minimum_questions", 0):
        reasons.append("Too few follow-up questions were returned.")
    term_groups = case["expect"].get("question_term_groups", [])
    if term_groups and not any(
        all(any(term in question.casefold() for term in group) for group in term_groups)
        for question in questions
    ):
        reasons.append("No question asked for the tire pressure reading or check result.")
    if case["expect"].get("questions_must_not_mention_vin") and any(
        re.search(r"\bvin\b|\bvehicle identification number\b", question, flags=re.IGNORECASE)
        for question in questions
    ):
        reasons.append("A question requested a VIN already present in vehicle context.")

    handoff = result.get("handoff", "").casefold()
    for phrase in case["expect"].get("handoff_must_not_contain", []):
        if phrase.casefold() in handoff:
            reasons.append(f"Handoff repeated the instruction to say '{phrase}'.")

    if not reasons:
        return {"pass": True, "score": 1, "reason": "The declared structural expectation passed."}
    return {"pass": False, "score": 0, "reason": " ".join(reasons)}
