"""Service intake review prototype.

Minimal Streamlit UI over intake.api. Saved examples render from
checked results without a model call. Editing a conversation enables a
live analysis run. Editing the conversation invalidates the shown
write-up until the next analysis.
"""

from __future__ import annotations

import html
import os

import streamlit as st
import streamlit.components.v1

from intake.api import get_settings, list_examples, parse_transcript, process_intake
from intake.evidence import value_matches_quote
from intake.ui_helpers import highlighted_text_html

WRITE_UP_VEHICLE_LABELS = {
    "vin": "VIN",
    "model": "Vehicle model",
    "year": "Vehicle year",
    "mileage": "Vehicle mileage",
}
SECRET_ENV_KEYS = (
    "INTAKE_API_KEY",
    "INTAKE_BASE_URL",
    "INTAKE_MODEL",
    "INTAKE_PROCESS_REQUEST_LIMIT",
)

EXAMPLES = list_examples()
EXAMPLE_BY_ID = {example["id"]: example for example in EXAMPLES}
OWN_ID = "own"
PICKER_OPTIONS = [example["id"] for example in EXAMPLES] + [OWN_ID]

CSS = """<style>
[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stHeaderActionElements"] { display: none; }
div[data-baseweb="base-input"],
div[data-baseweb="textarea"] { border-color: #c3cac0 !important; background-color: #ffffff; }
[data-testid="stTextAreaRootElement"] { border-color: #c3cac0 !important; }
[data-testid="stSelectbox"] .react-aria-ComboBox > div { border-color: #c3cac0 !important; }
[data-testid="stExpander"] details { border: 1px solid #ccd2c8; border-radius: 8px; }
.turns { display: flex; flex-direction: column; gap: 4px; margin-top: 6px;
  max-height: 34rem; overflow-y: auto; padding-right: 2px; }
.turn { background: #ffffff; border: 1px solid #e4e6e1; border-radius: 8px;
  padding: 5px 9px; }
.line-num { font-size: 11px; font-weight: 600; color: #68736b; margin-right: 6px; }
.speaker { font-size: 11px; font-weight: 600; color: #243c30; margin-right: 6px; }
.turn-text { font-size: 13.5px; color: #243c30; white-space: pre-wrap;
  overflow-wrap: anywhere; }
mark.ev { background: #dce9de; color: #243c30; padding: 0 2px; border-radius: 3px; }
.vehicle { font-size: 12px; color: #68736b; margin: 2px 0 4px; }
[class*="st-key-hl-"] button { padding: 0.1rem 0.5rem; min-height: 26px;
  font-size: 12px; line-height: 1; }
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] {
  padding-top: 2rem; padding-bottom: 1.5rem;
}
[data-testid="stAppViewContainer"] h1 { font-size: 2rem; line-height: 1.15; margin-bottom: 0.35rem; }
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3 { font-size: 1.25rem; margin-top: 0.5rem; }
[data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] { gap: 0.5rem; }
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


def _current_vehicle() -> dict[str, str]:
    vehicle = st.session_state.get("vehicle") or {}
    return dict(vehicle)


def _sync_editor() -> None:
    """Mirror the editor widget into the plain transcript key and mark it edited."""
    st.session_state["transcript"] = st.session_state["editor_text"]
    st.session_state["dirty"] = True


def _store_result(result: dict, kind: str, loaded_id: str | None) -> None:
    st.session_state["result"] = result
    st.session_state["result_kind"] = kind
    st.session_state["loaded_id"] = loaded_id
    st.session_state["dirty"] = False
    st.session_state["highlight"] = []


def _load_example(example_id: str) -> None:
    example = EXAMPLE_BY_ID[example_id]
    vehicle = {k: v for k, v in example["vehicle"].items() if v}
    st.session_state["transcript"] = example["transcript"]
    st.session_state["editor_text"] = example["transcript"]
    st.session_state["vehicle"] = vehicle
    st.session_state["editing"] = False
    result = process_intake(
        example["transcript"], vehicle, saved_result=example["result"]
    )
    _store_result(result, "saved", example["id"])


def _on_load_example() -> None:
    selection = st.session_state.get("example_select")
    if selection == OWN_ID:
        st.session_state["last_pick"] = OWN_ID
        _start_own_conversation()
        return
    if selection in EXAMPLE_BY_ID:
        st.session_state["last_pick"] = selection
        _load_example(selection)
        return
    # A click on the selected pill deselects it; restore the previous pick.
    st.session_state["example_select"] = st.session_state.get(
        "last_pick", EXAMPLES[0]["id"]
    )


def _start_own_conversation() -> None:
    st.session_state["transcript"] = ""
    st.session_state["editor_text"] = ""
    st.session_state["vehicle"] = {}
    st.session_state["editing"] = True
    st.session_state["highlight"] = []
    st.session_state["result"] = None
    st.session_state["result_kind"] = "draft"
    st.session_state["loaded_id"] = None
    st.session_state["dirty"] = False


def _enter_edit() -> None:
    """When edit mode opens, seed the editor from the durable transcript."""
    if st.session_state.get("editing"):
        st.session_state["editor_text"] = st.session_state["transcript"]


def _set_highlight(items: list[dict[str, str]]) -> None:
    st.session_state["highlight"] = [dict(item) for item in items]
    st.session_state["scroll_seq"] = st.session_state.get("scroll_seq", 0) + 1


def _boot() -> None:
    if st.session_state.get("booted"):
        return
    st.session_state["example_select"] = EXAMPLES[0]["id"]
    st.session_state["last_pick"] = EXAMPLES[0]["id"]
    st.session_state["editing"] = False
    st.session_state["highlight"] = []
    st.session_state["scroll_seq"] = 0
    _load_example(EXAMPLES[0]["id"])
    st.session_state["booted"] = True


def _turns_html(turns: list[dict[str, str]], highlight: dict[str, list[str]]) -> str:
    parts = ['<div class="turns">']
    for index, turn in enumerate(turns, start=1):
        text = highlighted_text_html(turn["text"], highlight.get(turn["id"], []))
        parts.append(
            f'<div class="turn" id="turn-{index}"><span class="line-num">'
            + str(index)
            + "</span>"
            + '<span class="speaker">'
            + html.escape(turn["speaker"])
            + "</span>"
            + '<span class="turn-text">'
            + text
            + "</span></div>"
        )
    parts.append("</div>")
    return "".join(parts)


def _scroll_to_line(line: int) -> None:
    """Center a turn inside the conversation pane only, without moving the page."""
    if line <= 0:
        return
    seq = st.session_state.get("scroll_seq", 0)
    st.components.v1.html(
        f"""<script>
        const seq = {seq};
        const doc = window.parent.document;
        let stable = 0;
        let ticks = 0;
        const timer = setInterval(() => {{
          ticks += 1;
          const container = doc.querySelector('.turns');
          const target = doc.getElementById('turn-{line}');
          let ok = false;
          if (container && target) {{
            const c = container.getBoundingClientRect();
            const r = target.getBoundingClientRect();
            const desired = container.scrollTop + (r.top - c.top)
              - (container.clientHeight - r.height) / 2;
            const limit = Math.max(0, container.scrollHeight - container.clientHeight);
            const clamped = Math.max(0, Math.min(desired, limit));
            if (Math.abs(container.scrollTop - clamped) > 1) {{
              container.scrollTop = clamped;
            }} else {{
              ok = true;
            }}
          }}
          stable = ok ? stable + 1 : 0;
          if (stable >= 5 || ticks > 40) clearInterval(timer);
        }}, 60);
        </script>""",
        height=0,
    )


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


def _supporting(field: str, values: list[str], evidence: list[dict]) -> list[dict]:
    """Keep only evidence quotes that contain one of the displayed values."""
    matching = [
        item
        for item in evidence
        if any(value_matches_quote(field, value, item["quote"]) for value in values)
    ]
    return matching or list(evidence)


_MD_ESCAPE = "\\`*_{}[]<>#|~"


def _md(text: str) -> str:
    """Escape call text so Markdown renders it literally."""
    escaped = str(text).replace("\\", "\\\\")
    for character in _MD_ESCAPE:
        escaped = escaped.replace(character, "\\" + character)
    return escaped


def _write_up_row(
    text: str,
    kind: str,
    row: int,
    evidence: list[dict],
    turns: list[dict[str, str]],
) -> None:
    if not evidence:
        st.markdown(text)
        return
    text_col, chip_col = st.columns([5, 2], vertical_alignment="center")
    with text_col:
        st.markdown(text)
    with chip_col:
        first = evidence[0]
        label = f"{first['speaker']}, line {_line_of(turns, first['turn_id'])}"
        if len(evidence) > 1:
            label += f" +{len(evidence) - 1}"
        st.button(
            label,
            key=f"hl-{kind}-{row}",
            on_click=_set_highlight,
            args=(
                [
                    {"turn_id": item["turn_id"], "quote": item["quote"]}
                    for item in evidence
                ],
            ),
        )


def _write_up(result: dict, vehicle: dict[str, str], turns: list[dict[str, str]]) -> None:
    with st.container(border=True):
        st.caption("SERVICE INTAKE DRAFT")
        if result.get("facts"):
            st.markdown("**Reported details**")
            for row, fact in enumerate(result["facts"]):
                _write_up_row(
                    f'**{fact["label"]}:** "{_md(fact["value"])}"',
                    "fact",
                    row,
                    _supporting(fact["field"], [fact["value"]], fact["evidence"]),
                    turns,
                )
        if result.get("corrections"):
            st.markdown("**Correction history**")
            for row, correction in enumerate(result["corrections"]):
                _write_up_row(
                    f'**{correction["field"].title()}:** '
                    f'"{_md(correction["previous_value"])}" → "{_md(correction["current_value"])}"',
                    "correction",
                    row,
                    _supporting(
                        correction["field"],
                        [correction["previous_value"], correction["current_value"]],
                        correction["evidence"],
                    ),
                    turns,
                )
        if result.get("conflicts"):
            st.markdown("**Unresolved conflicts**")
            for row, conflict in enumerate(result["conflicts"]):
                values = " or ".join(f'"{_md(value)}"' for value in conflict["values"])
                _write_up_row(
                    f'**{conflict["field"].title()}:** {values}',
                    "conflict",
                    row,
                    _supporting(conflict["field"], list(conflict["values"]), conflict["evidence"]),
                    turns,
                )
        if result.get("questions"):
            st.markdown("**Open questions**")
            for question in result["questions"]:
                st.markdown(f"- {_md(question)}")
        if vehicle:
            st.markdown("**Supplied vehicle context**")
            for field, value in vehicle.items():
                st.markdown(f"- {WRITE_UP_VEHICLE_LABELS[field]}: {_md(value)}")


def _worth_retrying(result: dict) -> bool:
    return any(
        "No write-up was generated." in error for error in result.get("errors", [])
    )


st.set_page_config(page_title="Service intake", layout="wide")
st.set_option("client.toolbarMode", "minimal")
st.markdown(CSS, unsafe_allow_html=True)

st.title("Service intake")
st.caption("A customer call becomes a technician write-up, where every detail cites the call.")

_boot()
if st.session_state.pop("close_editor", False):
    st.session_state["editing"] = False
_apply_secret_env()
settings = get_settings()
transcript = st.session_state["transcript"]
vehicle = _current_vehicle()
result = st.session_state.get("result")
stale = bool(result) and bool(st.session_state.get("dirty"))

st.pills(
    "Choose a conversation",
    options=PICKER_OPTIONS,
    format_func=lambda value: EXAMPLE_BY_ID[value]["title"] if value in EXAMPLE_BY_ID else "Your own",
    key="example_select",
    default=EXAMPLES[0]["id"],
    on_change=_on_load_example,
)

left, right = st.columns(2)

with left:
    st.subheader("Conversation")
    if vehicle and not st.session_state["editing"]:
        st.markdown(
            '<div class="vehicle">' + html.escape(_vehicle_line(vehicle)) + "</div>",
            unsafe_allow_html=True,
        )
    st.toggle("Edit conversation", key="editing", on_change=_enter_edit)
    if st.session_state["editing"]:
        st.text_area(
            "Conversation text",
            value=transcript,
            key="editor_text",
            max_chars=12000,
            height=260,
            on_change=_sync_editor,
            label_visibility="collapsed",
            placeholder=(
                "Paste or type the conversation, one turn per line. Example:\n"
                "Advisor: How can I help you today?\n"
                "Customer: There is a rattle over bumps in the morning."
            ),
        )
        st.caption("One turn per line, as 'Speaker: text'.")
        if settings.configured:
            analyze_clicked = st.button("Analyze conversation", key="analyze", type="primary")
        else:
            analyze_clicked = False
            st.button("Analyze conversation", key="analyze", type="primary", disabled=True)
            st.caption("Live analysis is unavailable on this deployment.")
        if analyze_clicked:
            with st.spinner("Analyzing..."):
                fresh = process_intake(transcript, vehicle)
                if _worth_retrying(fresh):
                    fresh = process_intake(transcript, vehicle)
            _store_result(fresh, "fresh", None)
            if fresh.get("valid"):
                # Show the analyzed call as conversation turns, not as the editor.
                st.session_state["close_editor"] = True
                st.rerun()
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
            selected = st.session_state.get("highlight") or []
            if selected:
                _scroll_to_line(_line_of(turns, selected[0]["turn_id"]))

with right:
    st.subheader("Technician write-up")
    if stale:
        st.warning("The conversation changed. Analyze again to update the write-up.")
    elif not result:
        st.info("Edit the conversation on the left, then click Analyze conversation.")
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
            _write_up(result, vehicle, turns)
            st.download_button(
                "Download draft",
                data=result["handoff"],
                file_name="service-intake-draft.txt",
                key="download_writeup",
            )
            st.caption("Click a source to see its words in the conversation.")
