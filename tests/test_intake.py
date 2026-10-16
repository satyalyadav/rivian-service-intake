from __future__ import annotations

from copy import deepcopy
import json

import httpx
import pytest

from evals.assertions import get_assert
from evals.cases import CASES, generate_tests
from intake import get_settings, list_examples, parse_transcript, process_intake
from intake import provider
from intake.examples import examples
from intake.provider import parse_model_content
from intake.schema import OutputValidationError


@pytest.mark.parametrize("example", examples, ids=lambda example: example["id"])
def test_saved_examples_use_the_shared_validation_and_render_path(example: dict) -> None:
    result = process_intake(
        example["transcript"], example["vehicle"], saved_result=example["result"]
    )

    assert result["source"] == "saved"
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["handoff"].startswith("SERVICE INTAKE DRAFT")
    assert result["model"] == get_settings().model
    assert all(set(fact) == {"id", "field", "label", "value", "evidence"} for fact in result["facts"])


def test_examples_are_isolated_copies() -> None:
    first = list_examples()
    first[0]["result"]["facts"].clear()
    assert list_examples()[0]["result"]["facts"]


def test_parser_preserves_text_after_separator_exactly() -> None:
    turns = parse_transcript("Customer:  two leading and trailing spaces  \n\nAdvisor: end")

    assert turns == [
        {"id": "T1", "speaker": "Customer", "text": " two leading and trailing spaces  "},
        {"id": "T2", "speaker": "Advisor", "text": "end"},
    ]


@pytest.mark.parametrize("transcript", ["Customer says hi", " customer: hello", "Customer:hello", "1Advisor: hi"])
def test_parser_rejects_invalid_speaker_or_separator(transcript: str) -> None:
    with pytest.raises(ValueError, match="Line 1"):
        parse_transcript(transcript)


def test_input_limits_fail_with_an_empty_handoff() -> None:
    too_long = process_intake("Customer: " + "x" * 12_000, {})
    bad_vehicle = process_intake(
        "Customer: The warning appeared today.", {"vin": "x" * 33}
    )

    assert too_long["valid"] is False and too_long["handoff"] == ""
    assert "12,000" in too_long["errors"][0]
    assert bad_vehicle["valid"] is False and bad_vehicle["handoff"] == ""
    assert "VIN" in bad_vehicle["errors"][0]


def test_vehicle_fields_reject_unknown_or_non_text_values() -> None:
    unknown = process_intake("Customer: The warning appeared today.", {"make": "Rivian"})
    non_text = process_intake("Customer: The warning appeared today.", {"year": 2024})

    assert not unknown["valid"] and "unsupported field" in unknown["errors"][0]
    assert not non_text["valid"] and "text" in non_text["errors"][0]


@pytest.mark.parametrize("bad_reference", [
    {"turn_id": "T9", "speaker": "Customer", "quote": "tire pressure warning"},
    {"turn_id": "T1", "speaker": "Advisor", "quote": "tire pressure warning"},
    {"turn_id": "T1", "speaker": "Customer", "quote": "pressure is dangerously low"},
])
def test_invalid_evidence_blocks_handoff(bad_reference: dict[str, str]) -> None:
    example = examples[1]
    saved = deepcopy(example["result"])
    saved["facts"][0]["evidence"] = [bad_reference]

    result = process_intake(example["transcript"], example["vehicle"], saved_result=saved)

    assert result["valid"] is False
    assert result["handoff"] == ""
    assert "Evidence" in result["errors"][0]


@pytest.mark.parametrize(
    ("field", "value", "quote"),
    [
        ("mileage", "8,000 miles", "28,000 miles"),
        ("year", "202", "2024"),
        ("vin", "ABC123", "XABC123Y"),
    ],
)
def test_numeric_or_identifier_values_cannot_match_inside_larger_tokens(
    field: str, value: str, quote: str
) -> None:
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

    assert not result["valid"]
    assert result["handoff"] == ""


@pytest.mark.parametrize("section", ["facts", "corrections", "conflicts"])
def test_mileage_boundary_check_applies_to_every_evidence_shape(section: str) -> None:
    transcript = "Customer: The odometer reads 28,000 miles.\nAdvisor: The file also says 28,000 miles."
    source_one = {"turn_id": "T1", "speaker": "Customer", "quote": "28,000 miles"}
    source_two = {"turn_id": "T2", "speaker": "Advisor", "quote": "28,000 miles"}
    candidate = {"facts": [], "corrections": [], "conflicts": [], "questions": []}
    if section == "facts":
        candidate["facts"] = [{"id": "F1", "field": "mileage", "value": "8,000 miles", "evidence": [source_one]}]
    elif section == "corrections":
        candidate["facts"] = [{"id": "F1", "field": "mileage", "value": "28,000 miles", "evidence": [source_one]}]
        candidate["corrections"] = [{
            "field": "mileage",
            "previous_value": "8,000 miles",
            "current_value": "28,000 miles",
            "evidence": [source_one, source_two],
        }]
    else:
        candidate["conflicts"] = [{
            "field": "mileage",
            "values": ["8,000 miles", "28,000 miles"],
            "evidence": [source_one, source_two],
        }]

    result = process_intake(transcript, {}, saved_result=candidate)

    assert not result["valid"]
    assert result["handoff"] == ""


def test_renderer_attributes_mileage_to_a_quote_with_the_full_value() -> None:
    result = process_intake(
        "Advisor: The old file says 28,000 miles.\nCustomer: I now read 8,000 miles.",
        {},
        saved_result={
            "facts": [{"id": "F1", "field": "mileage", "value": "8,000 miles", "evidence": [
                {"turn_id": "T1", "speaker": "Advisor", "quote": "28,000 miles"},
                {"turn_id": "T2", "speaker": "Customer", "quote": "8,000 miles"},
            ]}],
            "corrections": [],
            "conflicts": [],
            "questions": [],
        },
    )

    assert result["valid"]
    assert '- Mileage: "8,000 miles" (Customer, T2)' in result["handoff"]


def test_correction_with_reversed_source_chronology_is_rejected() -> None:
    result = process_intake(
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

    assert not result["valid"]
    assert "out of order" in result["errors"][0]


def test_extraction_rejects_extra_schema_fields_and_spoofed_handoff() -> None:
    example = examples[1]
    saved = deepcopy(example["result"])
    saved["facts"][0]["unreviewed"] = True
    saved["handoff"] = "APPROVED"

    result = process_intake(example["transcript"], example["vehicle"], saved_result=saved)

    assert not result["valid"]
    assert result["handoff"] == ""
    assert "structured format" in result["errors"][0]


def test_model_evidence_must_be_a_json_array() -> None:
    candidate = deepcopy(examples[0]["result"])
    candidate["facts"][0]["evidence"] = candidate["facts"][0]["evidence"][0]

    with pytest.raises(OutputValidationError, match="structured format"):
        parse_model_content(json.dumps(candidate))


def test_model_accepts_only_one_full_json_fence() -> None:
    candidate = json.dumps(examples[0]["result"])
    assert parse_model_content(f"```json\n{candidate}\n```").facts

    with pytest.raises(OutputValidationError):
        parse_model_content(f"Here is the result:\n```json\n{candidate}\n```")
    with pytest.raises(OutputValidationError):
        parse_model_content(f"```json\n{candidate}\n```\n```json\n{candidate}\n```")


def test_resolved_and_unresolved_values_cannot_share_a_field() -> None:
    example = examples[3]
    saved = deepcopy(example["result"])
    saved["facts"] = [{
        "id": "F1",
        "field": "mileage",
        "value": "41,000 miles",
        "evidence": [{"turn_id": "T1", "speaker": "Customer", "quote": "41,000 miles"}],
    }]

    result = process_intake(example["transcript"], example["vehicle"], saved_result=saved)

    assert not result["valid"]
    assert result["handoff"] == ""
    assert "resolved fact" in result["errors"][0]


def test_multiple_independent_concerns_can_share_a_field() -> None:
    transcript = "Customer: I hear a clunk and a rattle."
    saved = {
        "facts": [
            {"id": "F1", "field": "concern", "value": "clunk", "evidence": [
                {"turn_id": "T1", "speaker": "Customer", "quote": "clunk"}
            ]},
            {"id": "F2", "field": "concern", "value": "rattle", "evidence": [
                {"turn_id": "T1", "speaker": "Customer", "quote": "rattle"}
            ]},
        ],
        "corrections": [],
        "conflicts": [],
        "questions": [],
    }

    result = process_intake(transcript, {}, saved_result=saved)

    assert result["valid"]
    assert [fact["value"] for fact in result["facts"]] == ["clunk", "rattle"]


def test_handoff_attributes_value_to_evidence_that_contains_it() -> None:
    transcript = "Customer: I drive an R1T.\nAdvisor: You also mentioned a whine."
    saved = {
        "facts": [{
            "id": "F1",
            "field": "noise",
            "value": "whine",
            "evidence": [
                {"turn_id": "T1", "speaker": "Customer", "quote": "R1T"},
                {"turn_id": "T2", "speaker": "Advisor", "quote": "whine"},
            ],
        }],
        "corrections": [],
        "conflicts": [],
        "questions": [],
    }

    result = process_intake(transcript, {}, saved_result=saved)

    assert result["valid"]
    assert '- Noise: "whine" (Advisor, T2)' in result["handoff"]


def test_known_vin_filter_does_not_drop_questions_about_driving() -> None:
    example = examples[4]
    saved = deepcopy(example["result"])
    saved["questions"] = ["Could the driving noise change at speed?"]

    result = process_intake(example["transcript"], example["vehicle"], saved_result=saved)

    assert result["valid"]
    assert result["questions"] == ["Could the driving noise change at speed?"]


def test_live_mode_does_not_fall_back_to_saved_example_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTAKE_API_KEY", raising=False)
    example = examples[0]

    result = process_intake(example["transcript"], example["vehicle"])

    assert result["source"] == "live"
    assert result["valid"] is False
    assert result["handoff"] == ""
    assert "INTAKE_API_KEY" in result["errors"][0]


def test_settings_representation_never_includes_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-secret-value")
    settings = get_settings()

    assert settings.configured
    assert "glm-5.3-flash" in repr(settings)
    assert "test-secret-value" not in repr(settings)


def test_invalid_configured_base_url_returns_safe_error_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    monkeypatch.setenv("INTAKE_BASE_URL", "http://example.com/v1")
    settings = get_settings()
    result = process_intake("Customer: The warning appeared today.", {})

    assert settings._base_url == ""
    assert settings.configuration_error
    assert not result["valid"]
    assert result["handoff"] == ""
    assert "INTAKE_BASE_URL" in result["errors"][0]


def test_provider_mock_transport_runs_the_live_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    monkeypatch.setenv("INTAKE_PROCESS_REQUEST_LIMIT", "2")
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

    request = captured["request"]
    body = captured["body"]
    assert result["source"] == "live" and result["valid"]
    assert "transcript" not in body
    assert body["max_tokens"] >= 10_000
    assert body["response_format"] == {"type": "json_object"}
    system_prompt = body["messages"][0]["content"]
    assert "Complete JSON Schema" in system_prompt
    assert "is always a JSON array" in system_prompt
    assert "never extract" in system_prompt.casefold()
    assert "distinct quotes from one turn" in system_prompt
    assert "pressure readings" in system_prompt
    assert request.headers["user-agent"] == "rivian-service-intake-demo/0.1"
    assert request.headers.get("x-opencode-session")
    assert request.headers["authorization"] == "Bearer test-only-secret"
    assert "test-only-secret" not in repr(get_settings())


@pytest.mark.parametrize(
    ("finish_reason", "content", "error_text"),
    [
        ("length", "{\"facts\":", "output limit"),
        ("stop", "", "no content"),
    ],
)
def test_empty_or_truncated_provider_content_blocks_handoff(
    monkeypatch: pytest.MonkeyPatch,
    finish_reason: str,
    content: str,
    error_text: str,
) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    monkeypatch.setattr(provider, "_request_count", 0)
    example = examples[0]
    original_client = httpx.Client
    response_data = {"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_data)

    def mock_client(*args: object, **kwargs: object) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(provider.httpx, "Client", mock_client)
    result = process_intake(example["transcript"], example["vehicle"])

    assert result["valid"] is False
    assert result["handoff"] == ""
    assert error_text in result["errors"][0]


def test_process_request_cap_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provider, "_request_count", 0)

    assert provider.reserve_request(1)
    assert not provider.reserve_request(1)
    assert provider.current_request_count() == 1


def test_promptfoo_contains_six_cases_through_same_pipeline() -> None:
    assert [case["id"] for case in CASES] == [example["id"] for example in examples]
    assert len(generate_tests()) == 6


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_saved_promptfoo_expectation(case: dict) -> None:
    result = process_intake(case["transcript"], case["vehicle"], saved_result=case["result"])
    output = json.dumps(result)

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("INTAKE_EVAL_MODE", "saved")
        assertion = get_assert(output, {"vars": {"case_id": case["id"]}})

    assert assertion["pass"], assertion["reason"]


def test_clean_intake_accepts_a_supported_concern_or_noise_fact() -> None:
    example = next(item for item in examples if item["id"] == "clean-intake")
    saved = deepcopy(example["result"])
    saved["facts"][0]["field"] = "concern"
    saved["facts"][0]["value"] = "grinding noise when I turn left slowly"
    saved["facts"][0]["evidence"][0]["quote"] = "I hear a grinding noise when I turn left slowly."
    result = process_intake(example["transcript"], example["vehicle"], saved_result=saved)

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("INTAKE_EVAL_MODE", "saved")
        assertion = get_assert(json.dumps(result), {"vars": {"case_id": "clean-intake"}})

    assert result["valid"]
    assert assertion["pass"], assertion["reason"]


def test_explicit_correction_accepts_two_quotes_from_the_same_turn() -> None:
    example = next(item for item in examples if item["id"] == "explicit-correction")
    result = process_intake(example["transcript"], example["vehicle"], saved_result=example["result"])

    assert result["valid"]
    assert result["corrections"][0]["evidence"] == [
        {"turn_id": "T1", "speaker": "Customer", "quote": "30,000 miles"},
        {"turn_id": "T1", "speaker": "Customer", "quote": "28,000 miles"},
    ]


def test_required_warning_phrase_matches_a_supported_full_sentence() -> None:
    example = next(item for item in examples if item["id"] == "vehicle-context")
    saved = deepcopy(example["result"])
    saved["facts"][0]["value"] = "tire pressure warning is showing on the dash"
    saved["facts"][0]["evidence"][0]["quote"] = (
        "tire pressure warning is showing on the dash"
    )
    result = process_intake(example["transcript"], example["vehicle"], saved_result=saved)

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("INTAKE_EVAL_MODE", "saved")
        assertion = get_assert(
            json.dumps(result), {"vars": {"case_id": "vehicle-context"}}
        )

    assert result["valid"]
    assert assertion["pass"], assertion["reason"]
