"""
app.py
Streamlit entry point for Pitchside Analytics.

Run with:
    streamlit run app.py

Uses StatsBomb's live open data by default. To run fully offline on the
built-in sample league instead:
    PITCHSIDE_DATA_SOURCE=sample streamlit run app.py
"""

import streamlit as st

from pitchside.service import MatchService, build_service
from pitchside.ui.app import run


@st.cache_resource
def _service() -> MatchService:
    # One service per server process, shared by every session, so the
    # source's cache isn't rebuilt on each rerun.
    return build_service()


run(_service())
