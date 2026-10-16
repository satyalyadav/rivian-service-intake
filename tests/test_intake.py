from __future__ import annotations

from copy import deepcopy
import json

import httpx
import pytest

from evals.assertions import get_assert
from evals.cases import CASES, generate_tests
from intake import get_settings, parse_transcript, process_intake
from intake import provider
from intake.examples import examples


def test_saved_examples_validate_and_render() -> None:
    for example in examples:
        result = process_intake(
            example["transcript"], example["vehicle"], saved_result=example["result"]
        )

        assert result["valid"] is True, example["id"]
        assert result["errors"] == [], example["id"]
        assert result["handoff"].startswith("SERVICE INTAKE DRAFT"), example["id"]
        assert result["model"] == get_settings().model, example["id"]


def test_parser_accepts_turns_and_rejects_bad_lines() -> None:
    turns = parse_transcript("Customer:  two spaces  \n\nAdvisor: end")

    assert turns == [
        {"id": "T1", "speaker": "Customer", "text": " two spaces  "},
        {"id": "T2", "speaker": "Advisor", "text": "end"},
    ]
    for bad in ("Customer says hi", " customer: hello", "Customer:hello", "1Advisor: hi"):
        with pytest.raises(ValueError, match="Line 1"):
            parse_transcript(bad)
    with pytest.raises(ValueError, match="12,000"):
        parse_transcript("Customer: " + "x" * 12_000)


def test_evidence_rules() -> None:
    example = examples[0]
    for bad_reference in (
        {"turn_id": "T9", "speaker": "Customer", "quote": "creaking sound"},
        {"turn_id": "T2", "speaker": "Advisor", "quote": "creaking sound"},
        {"turn_id": "T2", "speaker": "Customer", "quote": "a quote that is absent"},
    ):
        saved = deepcopy(example["result"])
        saved["facts"][0]["evidence"] = [bad_reference]

        result = process_intake(example["transcript"], example["vehicle"], saved_result=saved)

        assert result["valid"] is False and result["handoff"] == ""
        assert "Evidence" in result["errors"][0]

    def mileage_result(value: str) -> dict:
        return process_intake(
            "Customer: The odometer reads 28,000 miles.",
            {},
            saved_result={
                "facts": [{"id": "F1", "field": "mileage", "value": value, "evidence": [
                    {"turn_id": "T1", "speaker": "Customer", "quote": "28,000 miles"}
                ]}],
                "corrections": [],
                "conflicts": [],
                "questions": [],
            },
        )

    for field, value, quote in (
        ("mileage", "8,000 miles", "28,000 miles"),
        ("year", "202", "2024"),
        ("vin", "ABC123", "XABC123Y"),
    ):
        result = process_intake(
            f"Customer: The reported value is {quote}.",
            {},
            saved_result={
                "facts": [{"id": "F1", "field": field, "value": value, "evidence": [
                    {"turn_id": "T1", "speaker": "Customer", "quote": quote}
                ]}],
                "corrections": [],
                "conflicts": [],
                "questions": [],
            },
        )
        assert result["valid"] is False, (field, value)

    accepted = mileage_result("28,000 miles")
    assert accepted["valid"] is True
    assert '- Mileage: "28,000 miles" (Customer, line 1)' in accepted["handoff"]


def test_correction_and_conflict_rules() -> None:
    accepted = process_intake(
        "Customer: I have 30,000 miles. Sorry, it is 28,000 miles.",
        {},
        saved_result={
            "facts": [{"id": "F1", "field": "mileage", "value": "28,000 miles", "evidence": [
                {"turn_id": "T1", "speaker": "Customer", "quote": "28,000 miles"}
            ]}],
            "corrections": [{
                "field": "mileage",
                "previous_value": "30,000 miles",
                "current_value": "28,000 miles",
                "evidence": [
                    {"turn_id": "T1", "speaker": "Customer", "quote": "30,000 miles"},
                    {"turn_id": "T1", "speaker": "Customer", "quote": "28,000 miles"},
                ],
            }],
            "conflicts": [],
            "questions": [],
        },
    )
    assert accepted["valid"] is True
    assert accepted["corrections"][0]["previous_value"] == "30,000 miles"

    reversed_order = process_intake(
        "Customer: It is 28,000 miles, then 28,000 miles again.\n"
        "Advisor: Earlier you said 30,000 miles, then 30,000 miles again.",
        {},
        saved_result={
            "facts": [{"id": "F1", "field": "mileage", "value": "28,000 miles", "evidence": [
                {"turn_id": "T1", "speaker": "Customer", "quote": "28,000 miles, then 28,000 miles again"}
            ]}],
            "corrections": [{
                "field": "mileage",
                "previous_value": "30,000 miles",
                "current_value": "28,000 miles",
                "evidence": [
                    {"turn_id": "T2", "speaker": "Advisor", "quote": "30,000 miles, then 30,000 miles again"},
                    {"turn_id": "T1", "speaker": "Customer", "quote": "28,000 miles, then 28,000 miles again"},
                ],
            }],
            "conflicts": [],
            "questions": [],
        },
    )
    assert reversed_order["valid"] is False
    assert "out of order" in reversed_order["errors"][0]

    settled_and_unsettled = process_intake(
        "Customer: The odometer reads 41,000 miles.\nAdvisor: The file lists 47,000 miles.",
        {},
        saved_result={
            "facts": [{"id": "F1", "field": "mileage", "value": "41,000 miles", "evidence": [
                {"turn_id": "T1", "speaker": "Customer", "quote": "41,000 miles"}
            ]}],
            "corrections": [],
            "conflicts": [{
                "field": "mileage",
                "values": ["41,000 miles", "47,000 miles"],
                "evidence": [
                    {"turn_id": "T1", "speaker": "Customer", "quote": "41,000 miles"},
                    {"turn_id": "T2", "speaker": "Advisor", "quote": "47,000 miles"},
                ],
            }],
            "questions": [],
        },
    )
    assert settled_and_unsettled["valid"] is False
    assert "resolved fact" in settled_and_unsettled["errors"][0]

    partial_mileage = process_intake(
        "Advisor: The odometer reads 28,000 miles.\nCustomer: It reads 28,000 miles on my screen.",
        {},
        saved_result={
            "facts": [{"id": "F1", "field": "mileage", "value": "28,000 miles", "evidence": [
                {"turn_id": "T1", "speaker": "Advisor", "quote": "28,000 miles"}
            ]}],
            "corrections": [{
                "field": "mileage",
                "previous_value": "8,000 miles",
                "current_value": "28,000 miles",
                "evidence": [
                    {"turn_id": "T1", "speaker": "Advisor", "quote": "28,000 miles"},
                    {"turn_id": "T2", "speaker": "Customer", "quote": "28,000 miles"},
                ],
            }],
            "conflicts": [],
            "questions": [],
        },
    )
    assert partial_mileage["valid"] is False


def test_repeating_fields_can_carry_facts_alongside_a_conflict() -> None:
    transcript = (
        "Customer: The handles don't come out sometimes.\n"
        "Customer: The car doesn't respond either.\n"
        "Advisor: Are those the same problem?\n"
        "Customer: I'm not sure. Also the charger stops on its own."
    )
    saved = {
        "facts": [
            {"id": "F1", "field": "concern", "value": "the charger stops", "evidence": [
                {"turn_id": "T4", "speaker": "Customer", "quote": "the charger stops on its own"}
            ]},
            {"id": "F2", "field": "concern", "value": "The handles don't come out", "evidence": [
                {"turn_id": "T1", "speaker": "Customer", "quote": "The handles don't come out"}
            ]},
            {"id": "F3", "field": "other_detail", "value": "I'm not sure", "evidence": [
                {"turn_id": "T4", "speaker": "Customer", "quote": "I'm not sure"}
            ]},
        ],
        "corrections": [],
        "conflicts": [{
            "field": "concern",
            "values": ["The handles don't come out", "The car doesn't respond"],
            "evidence": [
                {"turn_id": "T1", "speaker": "Customer", "quote": "The handles don't come out"},
                {"turn_id": "T2", "speaker": "Customer", "quote": "The car doesn't respond"},
            ],
        }],
        "questions": [],
    }

    result = process_intake(transcript, {}, saved_result=saved)

    assert result["valid"] is True
    assert [fact["value"] for fact in result["facts"]] == ["the charger stops", "I'm not sure"]
    assert [fact["id"] for fact in result["facts"]] == ["F1", "F2"]
    assert result["conflicts"][0]["field"] == "concern"

    # The filtered result must pass the same validator if it is checked again.
    again = process_intake(
        transcript,
        {},
        saved_result={
            "facts": [
                {"id": fact["id"], "field": fact["field"], "value": fact["value"], "evidence": fact["evidence"]}
                for fact in result["facts"]
            ],
            "corrections": [],
            "conflicts": result["conflicts"],
            "questions": [],
        },
    )
    assert again["valid"] is True, again["errors"]


def test_dropping_every_fact_of_a_conflicted_field_stays_valid() -> None:
    transcript = (
        "Customer: The handles don't come out sometimes.\n"
        "Customer: The car doesn't respond either."
    )
    saved = {
        "facts": [{"id": "F1", "field": "concern", "value": "The handles don't come out", "evidence": [
            {"turn_id": "T1", "speaker": "Customer", "quote": "The handles don't come out"}
        ]}],
        "corrections": [],
        "conflicts": [{
            "field": "concern",
            "values": ["The handles don't come out", "The car doesn't respond"],
            "evidence": [
                {"turn_id": "T1", "speaker": "Customer", "quote": "The handles don't come out"},
                {"turn_id": "T2", "speaker": "Customer", "quote": "The car doesn't respond"},
            ],
        }],
        "questions": [],
    }

    result = process_intake(transcript, {}, saved_result=saved)

    assert result["valid"] is True
    assert result["facts"] == []

    again = process_intake(
        transcript,
        {},
        saved_result={
            "facts": result["facts"],
            "corrections": [],
            "conflicts": result["conflicts"],
            "questions": [],
        },
    )
    assert again["valid"] is True, again["errors"]


def test_strict_inputs_reject_bad_vehicle_values_and_extra_fields() -> None:
    unknown = process_intake("Customer: The warning appeared today.", {"make": "Rivian"})
    non_text = process_intake("Customer: The warning appeared today.", {"year": 2024})
    too_long_vin = process_intake("Customer: The warning appeared today.", {"vin": "x" * 33})

    assert not unknown["valid"] and "unsupported field" in unknown["errors"][0]
    assert not non_text["valid"] and "text" in non_text["errors"][0]
    assert not too_long_vin["valid"] and "VIN" in too_long_vin["errors"][0]

    saved = deepcopy(examples[0]["result"])
    saved["facts"][0]["unreviewed"] = True
    saved["handoff"] = "APPROVED"
    result = process_intake(
        examples[0]["transcript"], examples[0]["vehicle"], saved_result=saved
    )

    assert result["valid"] is False
    assert "structured format" in result["errors"][0]


def test_configuration_safety(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTAKE_API_KEY", raising=False)
    example = examples[0]

    result = process_intake(example["transcript"], example["vehicle"])

    assert result["source"] == "live" and result["valid"] is False
    assert result["handoff"] == ""
    assert "INTAKE_API_KEY" in result["errors"][0]

    monkeypatch.setenv("INTAKE_API_KEY", "test-secret-value")
    settings = get_settings()
    assert settings.configured
    assert "test-secret-value" not in repr(settings)


def test_provider_request_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    monkeypatch.setattr(provider, "_request_count", 0)
    example = examples[0]
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "choices": [{
                "message": {"content": f"```json\n{json.dumps(example['result'])}\n```"},
                "finish_reason": "stop",
            }]
        })

    original_client = httpx.Client

    def mock_client(*args: object, **kwargs: object) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(provider.httpx, "Client", mock_client)
    result = process_intake(example["transcript"], example["vehicle"])

    body = captured["body"]
    request = captured["request"]
    assert result["source"] == "live" and result["valid"]
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_tokens"] == 24_000
    assert "Complete JSON Schema" in body["messages"][0]["content"]
    assert request.headers["user-agent"] == "rivian-service-intake-demo/0.1"
    assert request.headers["authorization"] == "Bearer test-only-secret"

    def empty_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "choices": [{"message": {"content": ""}, "finish_reason": "stop"}]
        })

    monkeypatch.setattr(provider, "_request_count", 0)
    monkeypatch.setattr(
        provider.httpx,
        "Client",
        lambda *args, **kwargs: original_client(
            transport=httpx.MockTransport(empty_handler), **kwargs
        ),
    )
    empty = process_intake(example["transcript"], example["vehicle"])

    assert empty["valid"] is False and empty["handoff"] == ""
    assert "no content" in empty["errors"][0]


def test_request_cap_blocks_more_than_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provider, "_request_count", 0)

    assert provider.reserve_request(1)
    assert not provider.reserve_request(1)
    assert provider.current_request_count() == 1


def test_response_size_cap_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    example = examples[0]
    response_body = json.dumps({
        "choices": [{
            "message": {"content": json.dumps(example["result"])},
            "finish_reason": "stop",
        }]
    }).encode("utf-8")
    original_client = httpx.Client

    def run_with_cap(size_cap: int) -> dict:
        monkeypatch.setattr(provider, "_request_count", 0)
        monkeypatch.setattr(provider, "MAX_PROVIDER_RESPONSE_BYTES", size_cap)
        monkeypatch.setattr(
            provider.httpx,
            "Client",
            lambda *args, **kwargs: original_client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, content=response_body)
                ),
                **kwargs,
            ),
        )
        return process_intake(example["transcript"], example["vehicle"])

    accepted = run_with_cap(len(response_body))
    assert accepted["valid"] is True, accepted["errors"]

    rejected = run_with_cap(len(response_body) - 1)
    assert rejected["valid"] is False
    assert "size limit" in rejected["errors"][0]


def test_truncated_model_content_blocks_the_write_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    monkeypatch.setattr(provider, "_request_count", 0)
    example = examples[0]
    original_client = httpx.Client
    response_data = {
        "choices": [{"message": {"content": '{"facts":'}, "finish_reason": "length"}]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_data)

    def mock_client(*args: object, **kwargs: object) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(provider.httpx, "Client", mock_client)
    result = process_intake(example["transcript"], example["vehicle"])

    assert result["valid"] is False and result["handoff"] == ""
    assert "output limit" in result["errors"][0]


def test_promptfoo_cases_match_the_four_conversations() -> None:
    assert [case["id"] for case in CASES] == [example["id"] for example in examples]
    assert len(generate_tests()) == len(examples)

    for case in CASES:
        result = process_intake(case["transcript"], case["vehicle"], saved_result=case["result"])
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("INTAKE_EVAL_MODE", "saved")
            assertion = get_assert(json.dumps(result), {"vars": {"case_id": case["id"]}})
        assert assertion["pass"], assertion["reason"]
