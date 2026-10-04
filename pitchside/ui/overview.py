"""
The match overview: the summary strip above the tabs, or a button that
brings it back.

The strip is shown when a match is selected. As soon as the viewer moves
to another tab it shrinks to a "Match overview" button, leaving the
charts more room; the button shows the strip again.

What changed since the last run decides this, rather than a tab-change
callback, so the rule is one pure function (``overview_open``) and the
page can be driven by setting the open tab in session state, as the
tests do.
"""

from collections.abc import Hashable

import pandas as pd
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from pitchside.viz.tables import summary_html

OPEN_KEY = "overview_open"
SEEN_SELECTION_KEY = "overview_selection"
SEEN_VIEW_KEY = "overview_view"
BUTTON_KEY = "overview_button"
BUTTON_LABEL = "Match overview"


def overview_open(
    was_open: bool, previous_selection: Hashable | None, selection: Hashable,
    previous_view: str | None, view: str,
) -> bool:
    """Whether the strip should be shown on this run.

    Any new selection in the sidebar shows it (even one that lands on the
    match already shown, e.g. picking the current random match by name);
    moving to another tab hides it; otherwise it stays as it was (shown
    again only by the button).
    """
    if selection != previous_selection:
        return True
    if view != previous_view:
        return False
    return was_open


def _show() -> None:
    st.session_state[OPEN_KEY] = True


def render_overview(slot: DeltaGenerator, summary: pd.DataFrame, selection: Hashable, view: str) -> None:
    """Fill ``slot`` with the strip or the button, and remember this run.

    Args:
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
        if is_open:
            st.markdown(summary_html(summary), unsafe_allow_html=True)
        else:
            st.button(BUTTON_LABEL, key=BUTTON_KEY, icon=":material/bar_chart:", on_click=_show)
