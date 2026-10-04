"""The sidebar: match picker and display settings."""

import random

import streamlit as st
from streamlit.navigation.page import StreamlitPage

from pitchside.service import MatchRef, MatchService

RANDOM_LABEL = "🎲 Random match"
REDUCE_MOTION_KEY = "reduce_motion"
# Prefix of every match-picker widget key. Each dropdown's key includes the
# choices above it, so every country/competition/season remembers its own
# pick, and the keys can be kept alive while another page is open.
PICK_PREFIX = "pick_"


def random_key(competition_id: int, season_id: int) -> str:
    """Session-state key holding the random pick for one competition+season."""
    return f"random_match_{competition_id}_{season_id}"


def pick_match(service: MatchService) -> MatchRef:
    """Country -> Competition -> Season -> Match (optional) selectors.

    Stops the script with a warning if the chosen season has no matches.
    """
    st.header("Select a match")
    comps = service.competitions()

    country = st.selectbox(
        "Country", sorted(comps["country_name"].unique()), key=f"{PICK_PREFIX}country"
    )
    country_rows = comps[comps["country_name"] == country]

    competition_name = st.selectbox(
        "Competition", sorted(country_rows["competition_name"].unique()),
        key=f"{PICK_PREFIX}competition_{country}",
    )
    competition_rows = country_rows[country_rows["competition_name"] == competition_name]

    season_name = st.selectbox(
        "Season", sorted(competition_rows["season_name"].unique(), reverse=True),
        key=f"{PICK_PREFIX}season_{country}_{competition_name}",
    )
    comp_row = competition_rows[competition_rows["season_name"] == season_name].iloc[0]
    competition_id = int(comp_row["competition_id"])
    season_id = int(comp_row["season_id"])

    matches = service.matches(competition_id, season_id)
    if not matches:
        st.warning("No matches found for this selection.")
        st.stop()

    by_label = {m.label: m for m in matches}
    choice = st.selectbox("Match (optional)", [RANDOM_LABEL, *by_label],
                          key=f"{PICK_PREFIX}match_{competition_id}_{season_id}")
    if choice != RANDOM_LABEL:
        return by_label[choice]

    # Remember the random pick per competition+season so it doesn't
    # re-shuffle on every unrelated rerun (e.g. a tab click). The
    # Shuffle button deliberately re-rolls it.
    key = random_key(competition_id, season_id)
    match_ids = [m.match_id for m in matches]
    if st.session_state.get(key) not in match_ids:
        st.session_state[key] = random.choice(match_ids)
    if st.button("🔀 Shuffle random match"):
        st.session_state[key] = random.choice(match_ids)
    return next(m for m in matches if m.match_id == st.session_state[key])


def selection(match: MatchRef) -> tuple:
    """Everything the viewer has picked in the sidebar, plus the match it
    led to (which changes on Shuffle). Changes whenever they pick a match."""
    picks = sorted(
        (key, str(value)) for key, value in st.session_state.items()
        if isinstance(key, str) and key.startswith(PICK_PREFIX)
    )
    return (match.match_id, *picks)


def display_settings(data_label: str) -> None:
    """Display preferences, and where the data is coming from."""
    st.toggle(
        "Reduce motion",
        key=REDUCE_MOTION_KEY,
        help="Turn off tab transitions and entrance animations. They are "
             "also off whenever your device is set to reduce motion.",
    )
    st.caption(f"Data: {data_label}")


def page_link(label: str, page: StreamlitPage, key: str) -> None:
    """A text-style button that opens another page of the app."""
    if st.button(label, key=key, type="tertiary"):
        st.switch_page(page)
