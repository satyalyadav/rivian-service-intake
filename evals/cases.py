"""Four synthetic expectations written before model evaluation."""

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
    "noise-over-bumps": {
        "fact_alternatives": [{
            "fields": ["concern", "noise"],
            "value_contains": "creak",
        }],
        "required_facts": [{"field": "mileage", "value": "28,410 miles"}],
        "corrections": 0,
        "conflict_count": 0,
        "minimum_questions": 2,
    },
    "correction-and-conflict": {
        "required_facts": [{"field": "timing", "value": "closer to four weeks"}],
        "correction": {
            "field": "timing",
            "previous_value": "Around three weeks ago",
            "current_value": "closer to four weeks",
        },
        "conflicts": [{"field": "mileage", "values": ["41,000 miles", "47,000 miles"]}],
        "no_fact_fields": ["mileage"],
        "corrections": 1,
        "conflict_count": 1,
        "minimum_questions": 2,
    },
    "messy-call": {
        "required_facts": [{"field": "concern", "value": "radio"}],
        "no_fact_value_contains": ["car wash", "Route 9"],
        "corrections": 0,
        "conflict_count": 0,
        "minimum_questions": 2,
    },
    "missing-details": {
        "fact_alternatives": [{
            "fields": ["concern", "warning"],
            "value_contains": "tire pressure",
        }],
        "question_term_groups": [["tire", "pressure"], ["reading", "gauge", "check"]],
        "corrections": 0,
        "conflict_count": 0,
        "minimum_questions": 2,
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
