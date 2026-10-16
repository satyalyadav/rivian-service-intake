"""Service intake review prototype.

Minimal Streamlit UI over intake.api. Saved examples render from
hand-authored results without a model call. Fresh analysis calls the
live model pipeline. Editing any input invalidates the shown result.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import time

import streamlit as st

from intake.api import get_settings, list_examples, parse_transcript, process_intake
from intake.ui_helpers import highlighted_text_html
from intake.validation import VEHICLE_FIELD_LIMITS

ANALYZE_COOLDOWN_SECONDS = 10.0
VEHICLE_FIELDS = ("vin", "model", "year", "mileage")
VEHICLE_LABELS = {"vin": "VIN", "model": "Model", "year": "Year", "mileage": "Mileage"}

EXAMPLES = list_examples()
EXAMPLE_BY_ID = {example["id"]: example for example in EXAMPLES}

CSS = """<style>
.turns { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.turn { background: #ffffff; border: 1px solid #e4e6e1; border-radius: 8px;
  padding: 8px 10px; }
.turn-id { font-size: 12px; color: #68736b; margin-right: 6px; }
.speaker { font-size: 12px; font-weight: 600; color: #243c30; }
.turn-text { margin: 4px 0 0; font-size: 14px; color: #243c30;
  white-space: pre-wrap; overflow-wrap: anywhere; }
mark.ev { background: #dce9de; color: #243c30; padding: 0 2px; border-radius: 3px; }
.conflict { color: #936500; }
.src-quote { border-left: 3px solid #243c30; padding-left: 8px;
  margin: 6px 0; font-size: 13px; color: #243c30;
  white-space: pre-wrap; overflow-wrap: anywhere; }
.src-ref { font-size: 12px; color: #68736b; }
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] {
  padding-top: 2rem; padding-bottom: 1.5rem;
}
[data-testid="stAppViewContainer"] h1 { font-size: 2rem; line-height: 1.15; margin-bottom: 0.35rem; }
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3 { font-size: 1.25rem; margin-top: 0.5rem; }
[data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] { gap: 0.6rem; }
</style>"""


def _fingerprint(transcript: str, vehicle: dict[str, str]) -> str:
    payload = transcript + "\x00" + json.dumps(vehicle, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _current_vehicle() -> dict[str, str]:
    if not st.session_state.get("vehicle_enabled"):
        return {}
    vehicle: dict[str, str] = {}
    for field in VEHICLE_FIELDS:
        value = (st.session_state.get(f"veh_{field}") or "").strip()
        if value:
            vehicle[field] = value
    return vehicle


def _mark_dirty() -> None:
    st.session_state["dirty"] = True


def _evidence_options(result: dict) -> list[tuple[str, str, list[dict]]]:
    options: list[tuple[str, str, list[dict]]] = []
    for fact in result.get("facts", []):
        options.append((
            f"fact:{fact['id']}",
            f"{fact['id']} {fact['label']}: {fact['value'][:60]}",
            fact["evidence"],
        ))
    for index, correction in enumerate(result.get("corrections", [])):
        options.append((
            f"correction:{index}",
            f"Correction {correction['field']}: "
            f"{correction['previous_value'][:30]} to {correction['current_value'][:30]}",
            correction["evidence"],
        ))
    for conflict in result.get("conflicts", []):
        options.append((
            f"conflict:{conflict['field']}",
            f"Conflict {conflict['field']}: {'; '.join(conflict['values'])[:60]}",
            conflict["evidence"],
        ))
    return options


def _store_result(result: dict, kind: str, loaded_id: str | None) -> None:
    st.session_state["result"] = result
    st.session_state["result_kind"] = kind
    st.session_state["loaded_id"] = loaded_id
    st.session_state["analyzed_fp"] = _fingerprint(
        st.session_state["transcript_editor"], _current_vehicle()
    )
    st.session_state["dirty"] = False
    options = _evidence_options(result)
    st.session_state["evidence_key"] = options[0][0] if options else ""


def _on_load_example() -> None:
    example = EXAMPLE_BY_ID[st.session_state["example_select"]]
    vehicle = {k: v for k, v in example["vehicle"].items() if v}
    st.session_state["transcript_editor"] = example["transcript"]
    st.session_state["vehicle_enabled"] = bool(vehicle)
    for field in VEHICLE_FIELDS:
        st.session_state[f"veh_{field}"] = vehicle.get(field, "")
    result = process_intake(
        example["transcript"], vehicle, saved_result=example["result"]
    )
    _store_result(result, "saved", example["id"])


def _boot() -> None:
    if st.session_state.get("booted"):
        return
    st.session_state["example_select"] = EXAMPLES[0]["id"]
    st.session_state["last_analyze_ts"] = 0.0
    _on_load_example()
    st.session_state["booted"] = True


def _turns_html(turns: list[dict[str, str]], highlight: dict[str, list[str]]) -> str:
    parts = ['<div class="turns">']
    for turn in turns:
        text = highlighted_text_html(turn["text"], highlight.get(turn["id"], []))
        parts.append(
            '<div class="turn"><span class="turn-id">'
            + html.escape(turn["id"])
            + "</span> "
            + '<span class="speaker">'
            + html.escape(turn["speaker"])
            + "</span>"
            + '<p class="turn-text">' + text + "</p></div>"
        )
    parts.append("</div>")
    return "".join(parts)


def _evidence_html(items: list[dict]) -> str:
    parts = []
    for item in items:
        parts.append(
            '<div class="src-ref">'
            + html.escape(f"{item['turn_id']} ({item['speaker']})")
            + "</div>"
            + '<div class="src-quote">'
            + html.escape(item["quote"])
            + "</div>"
        )
    return "".join(parts)


st.set_page_config(page_title="Service intake", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

st.title("Service intake")
st.caption("Independent prototype. Synthetic data only. Human review required.")

_boot()
settings = get_settings()
transcript = st.session_state["transcript_editor"]
vehicle = _current_vehicle()
result = st.session_state.get("result")
stale = bool(result) and (
    st.session_state.get("dirty")
    or _fingerprint(transcript, vehicle) != st.session_state.get("analyzed_fp")
)

picker_left, picker_right = st.columns([3, 1], vertical_alignment="bottom")
with picker_left:
    st.selectbox(
        "Example",
        options=[example["id"] for example in EXAMPLES],
        format_func=lambda example_id: next(
            f"{e['title']} ({e['id']})" for e in EXAMPLES if e["id"] == example_id
        ),
        key="example_select",
    )
with picker_right:
    st.button("Load example", key="load_example", on_click=_on_load_example)

left, right = st.columns(2)

with left:
    st.subheader("Conversation")
    st.text_area(
        "Transcript",
        key="transcript_editor",
        max_chars=12000,
        height=220,
        on_change=_mark_dirty,
    )
    st.caption("One turn per line, as 'Speaker: text'.")
    with st.expander("Vehicle context (optional)"):
        st.checkbox(
            "Include vehicle context",
            key="vehicle_enabled",
            on_change=_mark_dirty,
        )
        if st.session_state["vehicle_enabled"]:
            for field in VEHICLE_FIELDS:
                st.text_input(
                    VEHICLE_LABELS[field],
                    key=f"veh_{field}",
                    max_chars=VEHICLE_FIELD_LIMITS[field],
                    on_change=_mark_dirty,
                )
    analyze_clicked = st.button(
        "Analyze transcript",
        key="analyze",
        type="primary",
        disabled=not settings.configured,
    )
    if not settings.configured:
        st.caption("Live analysis needs INTAKE_API_KEY set on the server.")
    else:
        st.caption("Runs a fresh model request.")
        st.caption("Live analysis sends the transcript and optional vehicle details to the model provider.")
    if analyze_clicked and settings.configured:
        now = time.monotonic()
        wait = ANALYZE_COOLDOWN_SECONDS - (now - st.session_state["last_analyze_ts"])
        if wait > 0:
            st.warning(f"Wait {math.ceil(wait)} seconds before running again.")
        else:
            st.session_state["last_analyze_ts"] = now
            with st.spinner("Running fresh model request..."):
                fresh = process_intake(transcript, vehicle)
            _store_result(fresh, "fresh", None)
            result = fresh
            stale = False

    st.subheader("Source")
    try:
        turns = parse_transcript(transcript)
    except ValueError as exc:
        st.error(str(exc))
        turns = []
    if turns:
        highlight: dict[str, list[str]] = {}
        if result and result.get("valid") and not stale:
            for option_key, _label, items in _evidence_options(result):
                if option_key == st.session_state.get("evidence_key"):
                    for item in items:
                        highlight.setdefault(item["turn_id"], []).append(item["quote"])
        st.html(_turns_html(turns, highlight))

with right:
    st.subheader("Review")
    if stale:
        st.warning(
            "Inputs changed since this result. "
            "Analyze again or reload the example."
        )
    elif not result:
        st.info("Load an example to see its saved result.")
    if result and not stale:
        if st.session_state.get("result_kind") == "saved":
            loaded = EXAMPLE_BY_ID.get(st.session_state.get("loaded_id") or "")
            st.markdown(f"Saved example: {loaded['title']}" if loaded else "Saved example")
            st.caption("Hand-authored result. No model call.")
        elif result.get("valid") and not result.get("errors"):
            st.markdown("Fresh model result")
            st.caption(f"Model {result.get('model')}.")
        else:
            st.markdown("Analysis could not finish")
        if not result.get("valid") or result.get("errors"):
            for error in result.get("errors", ["The result is not valid."]):
                st.error(error)
            st.caption("No handoff generated.")
        else:
            options = _evidence_options(result)
            if options:
                keys = [key for key, _label, _items in options]
                if st.session_state.get("evidence_key") not in keys:
                    st.session_state["evidence_key"] = keys[0]
                st.selectbox(
                    "Inspect evidence for",
                    options=keys,
                    format_func=lambda key: next(
                        label for opt, label, _items in options if opt == key
                    ),
                    key="evidence_key",
                )
                selected_items = next(
                    items for opt, _label, items in options
                    if opt == st.session_state["evidence_key"]
                )
                st.html(_evidence_html(selected_items))
            for fact in result.get("facts", []):
                st.text(f"{fact['label']}: {fact['value']}")
                refs = "; ".join(
                    f"{item['turn_id']} ({item['speaker']})"
                    for item in fact["evidence"]
                )
                st.text(f"Evidence: {refs}")
            for correction in result.get("corrections", []):
                st.text(
                    f"{correction['field']} correction: "
                    f"{correction['previous_value']} to {correction['current_value']}"
                )
                refs = "; ".join(
                    f"{item['turn_id']} ({item['speaker']})"
                    for item in correction["evidence"]
                )
                st.text(f"History: {refs}")
            for conflict in result.get("conflicts", []):
                st.html(
                    '<div class="conflict"><strong>'
                    + html.escape(f"Conflict: {conflict['field']}. ")
                    + html.escape("; ".join(conflict["values"]))
                    + "</strong></div>"
                )
                refs = "; ".join(
                    f"{item['turn_id']} ({item['speaker']})"
                    for item in conflict["evidence"]
                )
                st.text(f"Sources: {refs}")
            if result.get("questions"):
                st.markdown("**Open questions.**")
                for question in result["questions"]:
                    st.text(question)

if result and result.get("valid") and not stale and result.get("handoff"):
    st.subheader("Draft handoff")
    st.caption("Human review required. Copy or download after review.")
    st.code(result["handoff"], language=None)
    st.download_button(
        "Download handoff",
        data=result["handoff"],
        file_name="service-intake-draft.txt",
        key="download_handoff",
    )
    st.caption(
        "Exact quote matches show where the words appear. "
        "They do not prove a quote supports the claim."
    )
