from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

from intake import api, provider
from intake.examples import examples
from intake.ui_helpers import highlighted_text_html


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _run_app() -> AppTest:
    return AppTest.from_file(APP_PATH, default_timeout=8).run()


def _write_up_present(at: AppTest) -> bool:
    texts = [item.value for item in at.caption] + [item.value for item in at.markdown]
    return any("SERVICE INTAKE DRAFT" in (text or "") for text in texts)


def _conversation_html(at: AppTest) -> str:
    return "".join(str(item.value) for item in at.get("html"))


def test_analyze_click_replaces_saved_write_up(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")

    def mock_request(**_kwargs):
        return {
            "facts": [{
                "id": "F1",
                "field": "concern",
                "value": "creaking sound when I go over speed bumps",
                "evidence": [{
                    "turn_id": "T2",
                    "speaker": "Customer",
                    "quote": "creaking sound when I go over speed bumps",
                }],
            }],
            "corrections": [],
            "conflicts": [],
            "questions": ["Does the creaking change in cold weather?"],
        }

    monkeypatch.setattr(api, "request_extraction", mock_request)
    at = _run_app()
    assert _write_up_present(at)

    at.toggle(key="editing").set_value(True).run()
    at.button(key="analyze").click().run()

    assert at.session_state["result_kind"] == "fresh"
    write_up = at.session_state["result"]["handoff"]
    assert 'Concern: "creaking sound when I go over speed bumps"' in write_up
    assert "Noise:" not in write_up
    assert _write_up_present(at)


def test_conversation_edits_hide_the_old_write_up() -> None:
    at = _run_app()
    assert _write_up_present(at)

    at.toggle(key="editing").set_value(True).run()
    at.text_area(key="editor_text").set_value("Customer: I hear a changed sound.")
    at.run()

    assert not _write_up_present(at)
    assert any("The conversation changed." in item.value for item in at.warning)


def test_leaving_edit_mode_keeps_the_edited_conversation() -> None:
    at = _run_app()
    at.toggle(key="editing").set_value(True).run()
    edited = at.session_state["transcript"] + "\nCustomer: It also happens at night."
    at.text_area(key="editor_text").set_value(edited).run()
    at.toggle(key="editing").set_value(False).run()

    assert at.session_state["transcript"] == edited
    assert "It also happens at night." in _conversation_html(at)


def test_deselecting_the_selected_pill_keeps_the_conversation() -> None:
    from streamlit.proto.WidgetStates_pb2 import WidgetStates

    at = _run_app()
    transcript_before = at.session_state["transcript"]

    # A click on the selected pill sends an empty selection. AppTest's
    # unselect() does not produce that message, so send it directly.
    states = WidgetStates()
    widget = states.widgets.add()
    widget.id = at.pills[0].id
    widget.string_array_value.data.extend([])
    at._run(states)

    assert not at.exception
    assert at.session_state["example_select"] == "noise-over-bumps"
    assert at.session_state["transcript"] == transcript_before


def test_failed_source_check_runs_one_retry(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    calls = {"count": 0}

    def mock_request(**_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "facts": [{
                    "id": "F1",
                    "field": "noise",
                    "value": "humming",
                    "evidence": [{
                        "turn_id": "T2",
                        "speaker": "Customer",
                        "quote": "creaking sound",
                    }],
                }],
                "corrections": [],
                "conflicts": [],
                "questions": [],
            }
        return {
            "facts": [{
                "id": "F1",
                "field": "noise",
                "value": "creaking sound",
                "evidence": [{
                    "turn_id": "T2",
                    "speaker": "Customer",
                    "quote": "creaking sound",
                }],
            }],
            "corrections": [],
            "conflicts": [],
            "questions": [],
        }

    monkeypatch.setattr(api, "request_extraction", mock_request)
    at = _run_app()
    at.toggle(key="editing").set_value(True).run()
    at.button(key="analyze").click().run()

    assert calls["count"] == 2
    assert at.session_state["result"]["valid"] is True
    assert _write_up_present(at)


def test_invalid_saved_quote_displays_error_without_a_write_up(monkeypatch) -> None:
    altered_examples = deepcopy(examples)
    altered_examples[0]["result"]["facts"][0]["evidence"][0]["quote"] = "quote absent from the transcript"
    monkeypatch.setattr(api, "list_examples", lambda: deepcopy(altered_examples))

    at = _run_app()

    assert not _write_up_present(at)
    assert any("Evidence" in item.value for item in at.error)
    assert any("Analysis could not finish" in item.value for item in at.markdown)


def test_http_500_shows_safe_error_and_removes_the_saved_write_up(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    monkeypatch.setenv("INTAKE_PROCESS_REQUEST_LIMIT", "2")
    monkeypatch.setattr(provider, "_request_count", 0)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500, text="test-only-secret response detail")

    original_client = httpx.Client

    def mock_client(*args, **kwargs) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(provider.httpx, "Client", mock_client)
    at = _run_app()
    assert _write_up_present(at)

    at.toggle(key="editing").set_value(True).run()
    at.button(key="analyze").click().run()

    assert len(requests) == 1
    assert at.session_state["result_kind"] == "fresh"
    assert not _write_up_present(at)
    assert any("provider returned HTTP 500" in item.value for item in at.error)
    assert all("test-only-secret" not in item.value for item in at.error)
    assert any("Analysis could not finish" in item.value for item in at.markdown)


def test_reopening_the_editor_keeps_the_edited_conversation(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")

    def mock_request(**_kwargs):
        return {
            "facts": [{
                "id": "F1",
                "field": "noise",
                "value": "clunk",
                "evidence": [{
                    "turn_id": "T1",
                    "speaker": "Customer",
                    "quote": "clunk",
                }],
            }],
            "corrections": [],
            "conflicts": [],
            "questions": [],
        }

    monkeypatch.setattr(api, "request_extraction", mock_request)
    at = _run_app()
    at.toggle(key="editing").set_value(True).run()
    edited = "Customer: I hear a clunk."
    at.text_area(key="editor_text").set_value(edited).run()
    at.button(key="analyze").click().run()
    at.toggle(key="editing").set_value(False).run()
    at.button(key="hl-fact-0").click().run()
    at.toggle(key="editing").set_value(True).run()

    assert at.text_area(key="editor_text").value == edited
    assert _write_up_present(at)


def test_source_chip_cites_the_evidence_that_contains_the_value(monkeypatch) -> None:
    example = {
        "id": "boundaries",
        "title": "Boundary",
        "description": "Test fixture.",
        "transcript": "Advisor: You drive an R1T.\nCustomer: It has a whine.",
        "vehicle": {},
        "result": {
            "facts": [{
                "id": "F1",
                "field": "noise",
                "value": "whine",
                "evidence": [
                    {"turn_id": "T1", "speaker": "Advisor", "quote": "R1T"},
                    {"turn_id": "T2", "speaker": "Customer", "quote": "whine"},
                ],
            }],
            "corrections": [],
            "conflicts": [],
            "questions": [],
        },
    }
    altered = deepcopy(examples)
    altered[0] = example
    monkeypatch.setattr(api, "list_examples", lambda: deepcopy(altered))

    at = _run_app()
    button = at.button(key="hl-fact-0")
    label = getattr(button, "label", None) or button.proto.label

    assert "Customer" in label and "line 2" in label


def test_two_failed_source_checks_show_the_error_without_a_draft(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    calls = {"count": 0}

    def always_bad(**_kwargs):
        calls["count"] += 1
        return {
            "facts": [{
                "id": "F1",
                "field": "noise",
                "value": "humming",
                "evidence": [{
                    "turn_id": "T2",
                    "speaker": "Customer",
                    "quote": "creaking sound",
                }],
            }],
            "corrections": [],
            "conflicts": [],
            "questions": [],
        }

    monkeypatch.setattr(api, "request_extraction", always_bad)
    at = _run_app()
    at.toggle(key="editing").set_value(True).run()
    at.button(key="analyze").click().run()

    assert calls["count"] == 2
    assert not _write_up_present(at)
    assert any("Evidence" in item.value for item in at.error)
    assert not at.get("download_button")
    assert at.session_state["editing"] is True


def test_successful_analysis_renders_the_conversation_turns(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")

    def mock_request(**_kwargs):
        return {
            "facts": [{
                "id": "F1",
                "field": "noise",
                "value": "creaking sound",
                "evidence": [{
                    "turn_id": "T2",
                    "speaker": "Customer",
                    "quote": "creaking sound",
                }],
            }],
            "corrections": [],
            "conflicts": [],
            "questions": [],
        }

    monkeypatch.setattr(api, "request_extraction", mock_request)
    at = _run_app()
    at.toggle(key="editing").set_value(True).run()
    at.button(key="analyze").click().run()

    assert at.session_state["editing"] is False
    assert "class=\"turn\"" in _conversation_html(at)
    assert _write_up_present(at)


def test_source_button_highlights_the_quote_in_the_conversation() -> None:
    at = _run_app()
    assert "class=\"ev\"" not in _conversation_html(at)

    at.button(key="hl-fact-0").click().run()

    quote = "creaking sound when I go over speed bumps"
    assert at.session_state["highlight"] == [{"turn_id": "T2", "quote": quote}]
    assert f'<mark class="ev">{quote}</mark>' in _conversation_html(at)


def test_overlapping_highlights_escape_raw_text_before_marking() -> None:
    raw = 'keep mark class="ev" & <script>alert(1)</script>'
    marked = highlighted_text_html(
        raw,
        ['mark class="ev" & <script>alert(1)</script>', 'class="ev" & <script>'],
    )

    assert marked == (
        'keep <mark class="ev">mark class=&quot;ev&quot; &amp; '
        '&lt;script&gt;alert(1)&lt;/script&gt;</mark>'
    )
    assert marked.count('<mark class="ev">') == 1
    assert "<script>" not in marked
