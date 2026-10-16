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


def _pick_conversation(at: AppTest, conversation_id: str) -> None:
    at.pills[0].set_value(conversation_id).run()


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


def test_conversation_choices_restore_drafts_results_and_evidence_without_calls(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    calls = {"count": 0}

    def mock_request(**kwargs):
        calls["count"] += 1
        assert "clunk" in kwargs["transcript"]
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
    own_draft = "Customer: I hear a clunk near the front."
    example_id = examples[1]["id"]
    other_example_id = examples[2]["id"]

    _pick_conversation(at, "own")
    at.text_area(key="editor_text").set_value(own_draft).run()
    _pick_conversation(at, example_id)
    assert at.session_state["active_conversation_id"] == example_id
    assert calls["count"] == 0

    at.toggle(key="editing").set_value(True).run()
    edited_example = "Customer: This example has a private edit."
    at.text_area(key="editor_text").set_value(edited_example).run()
    _pick_conversation(at, other_example_id)
    _pick_conversation(at, example_id)
    assert at.session_state["transcript"] == edited_example
    assert at.session_state["editing"] is True
    assert at.session_state["dirty"] is True
    assert not _write_up_present(at)
    assert calls["count"] == 0

    _pick_conversation(at, "own")
    assert at.text_area(key="editor_text").value == own_draft
    assert at.session_state["editing"] is True
    assert at.session_state["result"] is None
    assert calls["count"] == 0

    at.button(key="analyze").click().run()
    assert calls["count"] == 1
    assert at.session_state["result_kind"] == "fresh"
    assert at.session_state["result"]["valid"] is True
    assert at.session_state["editing"] is False
    at.button(key="hl-fact-0").click().run()
    assert at.session_state["highlight"] == [{"turn_id": "T1", "quote": "clunk"}]

    result = at.session_state["result"]
    _pick_conversation(at, example_id)
    _pick_conversation(at, "own")
    assert at.session_state["transcript"] == own_draft
    assert at.session_state["result"] == result
    assert at.session_state["dirty"] is False
    assert at.session_state["editing"] is False
    assert at.session_state["highlight"] == [{"turn_id": "T1", "quote": "clunk"}]
    assert '<mark class="ev">clunk</mark>' in _conversation_html(at)
    assert _write_up_present(at)
    assert calls["count"] == 1


def test_failed_analysis_and_example_highlight_survive_choice_switches(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    calls = {"count": 0}

    def bad_request(**_kwargs):
        calls["count"] += 1
        return {
            "facts": [{
                "id": "F1",
                "field": "noise",
                "value": "humming",
                "evidence": [{
                    "turn_id": "T1",
                    "speaker": "Customer",
                    "quote": "quote that is absent",
                }],
            }],
            "corrections": [],
            "conflicts": [],
            "questions": [],
        }

    monkeypatch.setattr(api, "request_extraction", bad_request)
    at = _run_app()
    first_id = examples[0]["id"]
    second_id = examples[1]["id"]
    at.button(key="hl-fact-0").click().run()
    highlight = [{"turn_id": "T2", "quote": "creaking sound when I go over speed bumps"}]

    _pick_conversation(at, second_id)
    _pick_conversation(at, first_id)
    assert at.session_state["highlight"] == highlight
    assert "class=\"ev\"" in _conversation_html(at)

    _pick_conversation(at, "own")
    failed_draft = "Customer: The rear area has a humming sound."
    at.text_area(key="editor_text").set_value(failed_draft).run()
    at.button(key="analyze").click().run()
    assert calls["count"] == 1
    error = at.session_state["result"]["errors"][0]
    assert at.session_state["result"]["valid"] is False

    _pick_conversation(at, second_id)
    _pick_conversation(at, "own")
    assert at.session_state["result_kind"] == "fresh"
    assert at.session_state["result"]["errors"] == [error]
    assert at.session_state["transcript"] == failed_draft
    assert at.session_state["editing"] is True
    assert at.session_state["dirty"] is False
    assert not _write_up_present(at)
    assert any("Evidence" in item.value for item in at.error)
    assert calls["count"] == 1


def test_pending_analysis_disables_duplicate_and_shows_status(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    calls = {"count": 0}

    def mock_request(**_kwargs):
        calls["count"] += 1
        raise AssertionError("a pending conversation must not start another request")

    monkeypatch.setattr(api, "request_extraction", mock_request)
    at = _run_app()
    _pick_conversation(at, "own")
    state = at.session_state["conversation_states"]["own"]
    state["analysis_pending"] = True
    state["pending_revision"] = state["draft_revision"]
    at.session_state["analysis_pending"] = True

    at.run()

    assert at.button(key="analyze").proto.disabled is True
    assert any("Analysis is still running" in item.value for item in at.info)
    assert calls["count"] == 0


def test_unexpected_analysis_error_clears_pending_state(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    original_process = api.process_intake
    calls = {"count": 0}

    def raise_live_error(transcript, vehicle, *, saved_result=None):
        if saved_result is not None:
            return original_process(transcript, vehicle, saved_result=saved_result)
        calls["count"] += 1
        raise RuntimeError("unexpected test failure")

    monkeypatch.setattr(api, "process_intake", raise_live_error)
    at = _run_app()
    _pick_conversation(at, "own")
    at.text_area(key="editor_text").set_value("Customer: I hear a humming noise.").run()
    at.button(key="analyze").click().run()

    state = at.session_state["conversation_states"]["own"]
    assert calls["count"] == 1
    assert state["analysis_pending"] is False
    assert state["pending_revision"] is None
    assert at.session_state["analysis_pending"] is False
    assert state["result"]["valid"] is False
    assert "Analysis could not finish" in state["result"]["errors"][0]


def test_older_conversation_snapshots_get_pending_defaults() -> None:
    at = _run_app()
    conversation_id = at.session_state["active_conversation_id"]
    state = at.session_state["conversation_states"][conversation_id]
    for key in ("analysis_pending", "draft_revision", "pending_revision", "analysis_lock"):
        state.pop(key, None)

    at.run()

    migrated = at.session_state["conversation_states"][conversation_id]
    assert migrated["analysis_pending"] is False
    assert migrated["draft_revision"] == 0
    assert migrated["pending_revision"] is None
    assert migrated["analysis_lock"] is not None


def test_failed_source_check_does_not_repeat_the_model_call(monkeypatch) -> None:
    monkeypatch.setenv("INTAKE_API_KEY", "test-only-secret")
    calls = {"count": 0}

    def mock_request(**_kwargs):
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

    monkeypatch.setattr(api, "request_extraction", mock_request)
    at = _run_app()
    at.toggle(key="editing").set_value(True).run()
    at.button(key="analyze").click().run()

    assert calls["count"] == 1
    assert at.session_state["result"]["valid"] is False
    assert not _write_up_present(at)
    assert any("Evidence" in item.value for item in at.error)


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


def test_failed_source_check_shows_the_error_without_a_draft(monkeypatch) -> None:
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

    assert calls["count"] == 1
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
