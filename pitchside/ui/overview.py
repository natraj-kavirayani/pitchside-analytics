"""
The match overview: the summary strip above the tabs, which can shrink
into a pill-shaped "Match overview" button and grow back out of it.

The strip is shown when a match is selected. It shrinks to the pill when
the viewer presses its Minimize button or moves to another tab, leaving
the charts more room; the pill shows it again.

Why it is built this way: Streamlit redraws the page from the server, so
swapping the strip for a button would remove one element and add
another, and nothing could animate between them. Instead the overview is
always the same four elements in one container: a state marker, the
strip, the Minimize button and the pill. Only the marker's ``data-open``
changes. The CSS here lays the elements out from the marker (via
``:has()``), and ``pitchside.ui.motion`` adds the transitions, so the
same elements smoothly change shape, and the content below follows as
the container's height changes.

What changed since the last run decides open or closed, rather than a
tab-change callback, so the rule is one pure function (``overview_open``)
and the page can be driven by setting the open tab in session state, as
the tests do.
"""

import textwrap
from collections.abc import Hashable

import pandas as pd
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from pitchside.viz.tables import summary_html

OPEN_KEY = "overview_open"
SEEN_SELECTION_KEY = "overview_selection"
SEEN_VIEW_KEY = "overview_view"
CONTAINER_KEY = "ps-overview"
BUTTON_KEY = "overview_button"
BUTTON_LABEL = "Match overview"
MINIMIZE_KEY = "overview_minimize"
MINIMIZE_LABEL = "Minimize"

# Selectors for the overview's parts. Streamlit gives keyed elements an
# "st-key-<key>" class.
OVERVIEW = f".st-key-{CONTAINER_KEY}"
STATE = "ps-overview-state"
OPEN = f'{OVERVIEW}:has(.{STATE}[data-open="true"])'
CLOSED = f'{OVERVIEW}:has(.{STATE}[data-open="false"])'
STRIP = ".ps-summary"
PILL = f".st-key-{BUTTON_KEY}"
MINIMIZE = f".st-key-{MINIMIZE_KEY}"

# The strip, the Minimize button and the pill share one grid cell, so the
# container is as tall as the strip; when the strip shrinks to the pill's
# exact size, everything below moves up with it.
LAYOUT_CSS = textwrap.dedent(f"""
    /* --- Match overview ---------------------------------------------- */
    {OVERVIEW} {{ display: grid; grid-template-columns: minmax(0, 1fr); --ps-pill-w: 13rem; --ps-pill-h: 2.6rem; }}
    {OVERVIEW} > * {{ grid-area: 1 / 1; min-width: 0; }}
    {OVERVIEW} {STRIP} {{ box-sizing: border-box; width: 100%; height: auto; overflow: hidden; }}
    {MINIMIZE} {{ justify-self: center; align-self: start; width: auto !important; margin-top: 10px; z-index: 1; }}
    {PILL} {{ justify-self: start; align-self: start; width: auto !important; margin-top: 4px; }}
    {PILL} button {{ width: var(--ps-pill-w); min-height: var(--ps-pill-h); height: var(--ps-pill-h); }}
    {OPEN} {PILL} {{ visibility: hidden; opacity: 0; }}
    {CLOSED} {STRIP} {{
        width: var(--ps-pill-w); height: var(--ps-pill-h);
        padding: 0 !important; border-radius: 999px !important; border-color: #22c55e !important;
        opacity: 0; visibility: hidden;
    }}
    {CLOSED} {STRIP} > * {{ opacity: 0; }}
    {CLOSED} {MINIMIZE} {{ visibility: hidden; opacity: 0; }}
""").strip()


def overview_open(
    was_open: bool, previous_selection: Hashable | None, selection: Hashable,
    previous_view: str | None, view: str,
) -> bool:
    """Whether the strip should be shown on this run.

    Any new selection in the sidebar shows it (even one that lands on the
    match already shown, e.g. picking the current random match by name);
    moving to another tab hides it; otherwise it stays as it was (changed
    only by the Minimize button and the pill).
    """
    if selection != previous_selection:
        return True
    if view != previous_view:
        return False
    return was_open


def _set_open(is_open: bool) -> None:
    st.session_state[OPEN_KEY] = is_open


def state_marker(is_open: bool) -> str:
    """The hidden element whose ``data-open`` the CSS keys off."""
    return f'<span class="{STATE}" data-open="{str(is_open).lower()}" hidden></span>'


def render_overview(slot: DeltaGenerator, summary: pd.DataFrame, selection: Hashable, view: str) -> None:
    """Fill ``slot`` with the overview, and remember this run.

    Always draws the same four elements, open or closed, so the browser
    keeps them between runs and can animate the change.

    Args:
        slot: A container made with ``key=CONTAINER_KEY``.
        selection: Anything that changes whenever the viewer picks a match
            in the sidebar (see ``pitchside.ui.sidebar.selection``).
        view: Label of the open tab.
    """
    state = st.session_state
    is_open = overview_open(
        was_open=state.get(OPEN_KEY, True),
        previous_selection=state.get(SEEN_SELECTION_KEY),
        selection=selection,
        previous_view=state.get(SEEN_VIEW_KEY),
        view=view,
    )
    state[OPEN_KEY], state[SEEN_SELECTION_KEY], state[SEEN_VIEW_KEY] = is_open, selection, view

    with slot:
        st.markdown(state_marker(is_open), unsafe_allow_html=True)
        st.markdown(summary_html(summary), unsafe_allow_html=True)
        st.button(MINIMIZE_LABEL, key=MINIMIZE_KEY, type="tertiary", icon=":material/close_fullscreen:",
                  help="Shrink the match overview", on_click=_set_open, args=(False,))
        st.button(BUTTON_LABEL, key=BUTTON_KEY, icon=":material/bar_chart:",
                  on_click=_set_open, args=(True,))
