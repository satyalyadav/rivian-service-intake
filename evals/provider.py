"""Promptfoo provider that calls the same intake pipeline as the UI."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.cases import get_case
from intake.api import process_intake


def call_api(prompt: str, options: dict[str, Any], context: dict[str, Any]) -> dict[str, str]:
    case_id = context.get("vars", {}).get("case_id")
    if not isinstance(case_id, str):
        raise ValueError("Promptfoo test is missing case_id.")
    case = get_case(case_id)
    mode = os.getenv("INTAKE_EVAL_MODE", "saved").strip().casefold()
    if mode == "saved":
        result = process_intake(
            case["transcript"], case["vehicle"], saved_result=case["result"]
        )
    elif mode == "live":
        result = process_intake(case["transcript"], case["vehicle"])
    else:
        raise ValueError("INTAKE_EVAL_MODE must be 'saved' or 'live'.")
    return {"output": json.dumps(result, ensure_ascii=False)}
