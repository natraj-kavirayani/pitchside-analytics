"""
The Streamlit app, assembled from the theme, sidebar, views and pages.

``run()`` takes the ``MatchService`` as an argument instead of creating
it, so tests can run the real app on in-memory data (see
tests/component), and ``app.py`` decides which data source the deployed
app uses.

There are two pages: the match page (default, at "/") and the About page
(at "/about"). Streamlit's page menu is hidden; each page links to the
other with a text button at the bottom of the sidebar.
"""

import streamlit as st
from streamlit.navigation.page import StreamlitPage

from pitchside.service import MatchService
from pitchside.ui.about import render_about
from pitchside.ui.motion import apply_motion
from pitchside.ui.overview import CONTAINER_KEY as OVERVIEW_KEY
from pitchside.ui.overview import render_overview
from pitchside.ui.sidebar import (
    PICK_PREFIX,
    REDUCE_MOTION_KEY,
    display_settings,
    page_link,
    pick_match,
    selection,
)
from pitchside.ui.theme import apply_theme, render_header
from pitchside.ui.views import VIEWS, MatchContext

# Session-state key for the selected tab, so it survives reruns.
VIEW_KEY = "view"
ABOUT_BUTTON_KEY = "about_button"
BACK_BUTTON_KEY = "back_button"
ABOUT_LABEL = "About"
BACK_LABEL = "← Back to matches"


def keep_widget_state() -> None:
    """Keep the match picker and open tab while another page is open.

    Streamlit forgets a widget's value on any run that doesn't draw the
    widget, such as every run of the About page. Re-assigning the value at
    the start of each run keeps it, so coming back from About shows the
    same match on the same tab.
    """
    for key in list(st.session_state):
        if isinstance(key, str) and (key.startswith(PICK_PREFIX) or key == VIEW_KEY):
            st.session_state[key] = st.session_state[key]


def match_page(service: MatchService, about: StreamlitPage) -> None:
    with st.sidebar:
        # Containers fix the order on screen, so the settings and the About
        # link can be drawn first and still survive pick_match() stopping
        # the script.
        picker, settings, links = st.container(), st.container(), st.container()
    with settings:
        st.divider()
        display_settings(service.label)
    with links:
        page_link(ABOUT_LABEL, about, key=ABOUT_BUTTON_KEY)
    with picker:
        match = pick_match(service)

    st.subheader(match.label)
    # Drawn before the tabs, so a change to the overview reaches the browser
    # (and starts animating) while the open tab's chart is still being
    # built. The tab the viewer just picked is already in session state.
    open_view = st.session_state.get(VIEW_KEY) or VIEWS[0].label
    render_overview(st.container(key=OVERVIEW_KEY), service.summary(match.match_id),
                    selection(match), open_view)

    # on_change="rerun" makes tabs lazy: only the selected tab's view runs,
    # instead of building every chart on every interaction.
    ctx = MatchContext(service=service, match=match)
    tabs = st.tabs([view.label for view in VIEWS], key=VIEW_KEY, on_change="rerun")
    for tab, view in zip(tabs, VIEWS):
        if tab.open:
            with tab:
                view.render(ctx)


def about_page(service: MatchService, home: StreamlitPage) -> None:
    with st.sidebar:
        display_settings(service.label)
        page_link(BACK_LABEL, home, key=BACK_BUTTON_KEY)
    render_about()


def run(service: MatchService) -> None:
    st.set_page_config(page_icon="⚽", layout="wide")
    keep_widget_state()
    apply_theme([view.accent for view in VIEWS])
    # The toggle is drawn further down, but its value from the previous
    # run is already in session state, so this run's CSS can follow it.
    apply_motion(enabled=not st.session_state.get(REDUCE_MOTION_KEY, False))
    render_header()

    def matches() -> None:
        match_page(service, about)

    def about_pitchside() -> None:
        about_page(service, home)

    home = st.Page(matches, title="Pitchside Analytics", default=True)
    about = st.Page(about_pitchside, title="About · Pitchside Analytics", url_path="about")
    st.navigation([home, about], position="hidden").run()
