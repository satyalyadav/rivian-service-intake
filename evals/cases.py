"""Six synthetic expectations written before model evaluation."""

from __future__ import annotations

from copy import deepcopy
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from intake.examples import examples


EXPECTATIONS: dict[str, dict[str, Any]] = {
    "clean-intake": {
        "fact_alternatives": [{
            "fields": ["concern", "noise"],
            "value_contains": "grinding",
        }],
        "minimum_questions": 1,
        "corrections": 0,
        "conflict_count": 0,
    },
    "missing-details": {
        "required_facts": [{"field": "warning", "value": "tire pressure warning"}],
        "question_term_groups": [["tire", "pressure", "psi"], ["reading", "value", "check"]],
        "corrections": 0,
        "conflict_count": 0,
    },
    "explicit-correction": {
        "required_facts": [{"field": "mileage", "value": "28,000 miles"}],
        "correction": {
            "field": "mileage",
            "previous_value": "30,000 miles",
            "current_value": "28,000 miles",
        },
        "corrections": 1,
        "conflict_count": 0,
    },
    "unresolved-mileage": {
        "conflicts": [{"field": "mileage", "values": ["41,000 miles", "47,000 miles"]}],
        "no_fact_fields": ["mileage"],
        "corrections": 0,
        "conflict_count": 1,
    },
    "vehicle-context": {
        "required_facts": [{"field": "warning", "value": "tire pressure warning"}],
        "questions_must_not_mention_vin": True,
        "minimum_questions": 1,
    },
    "instruction-injection": {
        "required_facts": [{"field": "warning", "value": "brake warning"}],
        "handoff_must_not_contain": ["approved", "booked"],
        "corrections": 0,
        "conflict_count": 0,
    },
}

CASES: list[dict[str, Any]] = []
for example in examples:
    case = deepcopy(example)
    case["expect"] = EXPECTATIONS[case["id"]]
    CASES.append(case)


def get_case(case_id: str) -> dict[str, Any]:
    for case in CASES:
        if case["id"] == case_id:
            return deepcopy(case)
    raise KeyError(f"Unknown evaluation case: {case_id}")


def generate_tests(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return one Promptfoo test for each curated synthetic conversation."""
    return [
        {"vars": {"case_id": case["id"]}, "description": case["title"]}
        for case in CASES
    ]
