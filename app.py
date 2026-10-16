"""Service intake review prototype.

Minimal Streamlit UI over intake.api. Saved examples render from
checked results without a model call. Editing a conversation enables a
live analysis run. Editing any input invalidates the shown write-up.
"""

from __future__ import annotations

import hashlib
import html
import json
import os

import streamlit as st

from intake.api import get_settings, list_examples, parse_transcript, process_intake
from intake.ui_helpers import highlighted_text_html
from intake.validation import VEHICLE_FIELD_LIMITS

VEHICLE_FIELDS = ("vin", "model", "year", "mileage")
VEHICLE_LABELS = {"vin": "VIN", "model": "Model", "year": "Year", "mileage": "Mileage"}
SECRET_ENV_KEYS = (
    "INTAKE_API_KEY",
    "INTAKE_BASE_URL",
    "INTAKE_MODEL",
    "INTAKE_PROCESS_REQUEST_LIMIT",
)

EXAMPLES = list_examples()
EXAMPLE_BY_ID = {example["id"]: example for example in EXAMPLES}

CSS = """<style>
[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none; }
.turns { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.turn { background: #ffffff; border: 1px solid #e4e6e1; border-radius: 8px;
  padding: 8px 10px; }
.line-num { font-size: 12px; font-weight: 600; color: #68736b; margin-right: 6px; }
.speaker { font-size: 12px; font-weight: 600; color: #243c30; }
.turn-text { margin: 4px 0 0; font-size: 14px; color: #243c30;
  white-space: pre-wrap; overflow-wrap: anywhere; }
mark.ev { background: #dce9de; color: #243c30; padding: 0 2px; border-radius: 3px; }
.vehicle { font-size: 12px; color: #68736b; margin: 2px 0 4px; }
.note { background: #ffffff; border: 1px solid #e4e6e1; border-radius: 8px;
  padding: 14px 16px; }
.note-title { font-size: 11px; letter-spacing: 0.08em; font-weight: 700;
  color: #68736b; text-transform: uppercase; margin-bottom: 4px; }
.note-section { font-size: 14px; font-weight: 600; color: #243c30;
  margin: 10px 0 2px; }
.note-item { font-size: 14px; color: #243c30; margin: 2px 0 2px 2px; }
.note-item .bullet { color: #68736b; margin-right: 6px; }
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] {
  padding-top: 2rem; padding-bottom: 1.5rem;
}
[data-testid="stAppViewContainer"] h1 { font-size: 2rem; line-height: 1.15; margin-bottom: 0.35rem; }
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3 { font-size: 1.25rem; margin-top: 0.5rem; }
[data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] { gap: 0.6rem; }
</style>"""


def _apply_secret_env() -> None:
    """Copy Streamlit Cloud secrets into the environment when unset."""
    try:
        secrets = dict(st.secrets)
    except Exception:
        return
    for key in SECRET_ENV_KEYS:
        if key not in os.environ and key in secrets:
            os.environ[key] = str(secrets[key])


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


def _store_result(result: dict, kind: str, loaded_id: str | None) -> None:
    st.session_state["result"] = result
    st.session_state["result_kind"] = kind
    st.session_state["loaded_id"] = loaded_id
    st.session_state["analyzed_fp"] = _fingerprint(
        st.session_state["transcript_editor"], _current_vehicle()
    )
    st.session_state["dirty"] = False
    st.session_state["highlight"] = []


def _on_load_example() -> None:
    example = EXAMPLE_BY_ID[st.session_state["example_select"]]
    vehicle = {k: v for k, v in example["vehicle"].items() if v}
    st.session_state["transcript_editor"] = example["transcript"]
    st.session_state["vehicle_enabled"] = bool(vehicle)
    for field in VEHICLE_FIELDS:
        st.session_state[f"veh_{field}"] = vehicle.get(field, "")
    st.session_state["editing"] = False
    result = process_intake(
        example["transcript"], vehicle, saved_result=example["result"]
    )
    _store_result(result, "saved", example["id"])


def _set_highlight(turn_id: str, quote: str) -> None:
    st.session_state["highlight"] = [{"turn_id": turn_id, "quote": quote}]


def _boot() -> None:
    if st.session_state.get("booted"):
        return
    st.session_state["example_select"] = EXAMPLES[0]["id"]
    st.session_state["editing"] = False
    st.session_state["highlight"] = []
    _on_load_example()
    st.session_state["booted"] = True


def _turns_html(turns: list[dict[str, str]], highlight: dict[str, list[str]]) -> str:
    parts = ['<div class="turns">']
    for index, turn in enumerate(turns, start=1):
        text = highlighted_text_html(turn["text"], highlight.get(turn["id"], []))
        parts.append(
            '<div class="turn"><span class="line-num">'
            + str(index)
            + "</span>"
            + '<span class="speaker">'
            + html.escape(turn["speaker"])
            + "</span>"
            + '<p class="turn-text">' + text + "</p></div>"
        )
    parts.append("</div>")
    return "".join(parts)


def _note_html(note: str) -> str:
    parts = ['<div class="note">']
    for line in note.splitlines():
        if not line.strip():
            continue
        if line == "SERVICE INTAKE DRAFT":
            parts.append('<div class="note-title">' + html.escape(line) + "</div>")
        elif line.endswith(":") and not line.startswith("- "):
            parts.append('<div class="note-section">' + html.escape(line) + "</div>")
        elif line.startswith("- "):
            parts.append(
                '<div class="note-item"><span class="bullet">&bull;</span>'
                + html.escape(line[2:])
                + "</div>"
            )
        else:
            parts.append('<div class="note-item">' + html.escape(line) + "</div>")
    parts.append("</div>")
    return "".join(parts)


def _vehicle_line(vehicle: dict[str, str]) -> str:
    parts = []
    if vehicle.get("vin"):
        parts.append(f"VIN {vehicle['vin']}")
    if vehicle.get("model"):
        parts.append(vehicle["model"])
    if vehicle.get("year"):
        parts.append(vehicle["year"])
    if vehicle.get("mileage"):
        parts.append(f"{vehicle['mileage']} mi")
    return " · ".join(parts)


def _line_of(turns: list[dict[str, str]], turn_id: str) -> int:
    for index, turn in enumerate(turns, start=1):
        if turn["id"] == turn_id:
            return index
    return 0


def _source_buttons(
    kind: str, row: int, evidence: list[dict], turns: list[dict[str, str]]
) -> None:
    if not evidence:
        return
    columns = st.columns(min(len(evidence), 4))
    for index, item in enumerate(evidence):
        with columns[index % len(columns)]:
            st.button(
                f"{item['speaker']}, line {_line_of(turns, item['turn_id'])}",
                key=f"hl-{kind}-{row}-{index}",
                help=item["quote"],
                on_click=_set_highlight,
                args=(item["turn_id"], item["quote"]),
            )


st.set_page_config(page_title="Service intake", layout="wide")
st.set_option("client.toolbarMode", "minimal")
st.markdown(CSS, unsafe_allow_html=True)

st.title("Service intake")
st.caption("A customer call becomes a technician write-up, with a quote for every line.")

_boot()
_apply_secret_env()
settings = get_settings()
transcript = st.session_state["transcript_editor"]
vehicle = _current_vehicle()
result = st.session_state.get("result")
stale = bool(result) and (
    st.session_state.get("dirty")
    or _fingerprint(transcript, vehicle) != st.session_state.get("analyzed_fp")
)

st.selectbox(
    "Choose a conversation",
    options=[example["id"] for example in EXAMPLES],
    format_func=lambda example_id: EXAMPLE_BY_ID[example_id]["title"],
    key="example_select",
    on_change=_on_load_example,
)

left, right = st.columns(2)

with left:
    st.subheader("Conversation")
    if vehicle:
        st.markdown(
            '<div class="vehicle">' + html.escape(_vehicle_line(vehicle)) + "</div>",
            unsafe_allow_html=True,
        )
    st.toggle("Edit conversation", key="editing")
    if st.session_state["editing"]:
        st.text_area(
            "Conversation text",
            key="transcript_editor",
            max_chars=12000,
            height=260,
            on_change=_mark_dirty,
            label_visibility="collapsed",
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
        if settings.configured:
            analyze_clicked = st.button("Analyze conversation", key="analyze", type="primary")
        else:
            analyze_clicked = False
            st.button("Analyze conversation", key="analyze", type="primary", disabled=True)
            st.caption("Live analysis is unavailable on this deployment.")
        if analyze_clicked:
            with st.spinner("Analyzing..."):
                fresh = process_intake(transcript, vehicle)
            _store_result(fresh, "fresh", None)
            result = fresh
            stale = False
    else:
        try:
            turns = parse_transcript(transcript)
        except ValueError as exc:
            turns = []
            st.error(str(exc))
        if turns:
            highlight: dict[str, list[str]] = {}
            for item in st.session_state.get("highlight", []):
                highlight.setdefault(item["turn_id"], []).append(item["quote"])
            st.html(_turns_html(turns, highlight))

with right:
    st.subheader("Technician write-up")
    if stale:
        st.warning("The conversation changed. Analyze again to update the write-up.")
    elif not result:
        st.info("Load an example to see its saved result.")
    if result and not stale:
        if not result.get("valid") or result.get("errors") or not result.get("handoff"):
            st.markdown("**Analysis could not finish**")
            for error in result.get("errors", ["The result is not valid."]):
                st.error(error)
        else:
            try:
                turns = parse_transcript(transcript)
            except ValueError:
                turns = []
            st.html(_note_html(result["handoff"]))
            st.download_button(
                "Download draft",
                data=result["handoff"],
                file_name="service-intake-draft.txt",
                key="download_writeup",
            )
            st.caption("Click a source to highlight it in the conversation.")
            if result.get("facts"):
                st.markdown("**What we know**")
                for row, fact in enumerate(result["facts"]):
                    with st.container(border=True):
                        st.markdown(f"**{fact['label']}:** {fact['value']}")
                        _source_buttons("fact", row, fact["evidence"], turns)
            if result.get("corrections"):
                st.markdown("**What changed**")
                for row, correction in enumerate(result["corrections"]):
                    with st.container(border=True):
                        st.markdown(
                            f"**{correction['field'].title()}:** "
                            f"{correction['previous_value']} → {correction['current_value']}"
                        )
                        _source_buttons("correction", row, correction["evidence"], turns)
            if result.get("conflicts"):
                st.markdown("**Still unclear**")
                for row, conflict in enumerate(result["conflicts"]):
                    with st.container(border=True):
                        values = " or ".join(conflict["values"])
                        st.markdown(f"**{conflict['field'].title()}:** {values}")
                        _source_buttons("conflict", row, conflict["evidence"], turns)
            if result.get("questions"):
                st.markdown("**Ask the customer**")
                for question in result["questions"]:
                    st.markdown(f"- {question}")
