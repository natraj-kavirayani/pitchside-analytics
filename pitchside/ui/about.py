"""The About page."""

import streamlit as st

# Key of the container holding the page, so the motion CSS can target it
# (Streamlit gives keyed containers an "st-key-<key>" class).
ABOUT_CONTAINER_KEY = "ps-about"


def render_about() -> None:
    with st.container(key=ABOUT_CONTAINER_KEY):
        st.markdown("### About Pitchside Analytics")
        st.write(
            "Pitchside Analytics is a tool for exploring football matches through "
            "StatsBomb's free open event data — shot maps, an xG timeline, pass "
            "maps, pass networks, touch heatmaps, and match details like lineups, "
            "managers, and substitutions — without needing to write any code or "
            "touch a spreadsheet."
        )

        st.markdown("### Who made this")
        st.write(
            "Built by Natraj, a Software Engineer with a background in "
            "automotive embedded software testing and QA. This app "
            "is a personal side project bringing that engineering/testing "
            "background together with an interest in football analytics."
        )

        st.markdown("### Status")
        st.write(
            "This is a work in progress. Planned additions include multi-match "
            "and season-level aggregate stats and the ability to export charts "
            "as images. Feedback and feature ideas are welcome."
        )
