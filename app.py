"""
app.py
Streamlit front-end for exploring StatsBomb open data.

Run with:
    streamlit run app.py
"""

import random
from dataclasses import dataclass

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from data_loader import (
    get_competitions,
    get_matches,
    get_events,
    get_shots,
    get_passes,
    get_starting_xi,
    get_substitutions,
    get_managers,
    get_pass_network,
    get_shootout,
    get_xg_timeline,
    teams_in_match,
)
from visualizations import (
    plot_heatmap,
    plot_pass_map,
    plot_pass_network,
    plot_shot_map,
    plot_xg_timeline,
    shootout_table_html,
)
from styling import apply_custom_style, render_header

RANDOM_LABEL = "🎲 Random match"
TAB_LABELS = [
    "Shot map", "xG timeline", "Pass map", "Pass network",
    "Touch heatmap", "Match details", "About",
]


@dataclass
class Selection:
    """The match chosen in the sidebar, plus the context needed to render it."""

    competition_id: int
    season_id: int
    match_id: int
    label: str
    home_team: str
    events: pd.DataFrame


def _match_labels(matches: pd.DataFrame) -> pd.Series:
    """Build "Home 2 - 1 Away (date)" labels for the match dropdown."""
    return (
        matches["home_team"] + " " + matches["home_score"].astype(str)
        + " - " + matches["away_score"].astype(str) + " " + matches["away_team"]
        + " (" + matches["match_date"].astype(str) + ")"
    )


def render_sidebar() -> Selection:
    """Country -> Competition -> Season -> Match (optional) selectors.

    Stops the script with a warning if the chosen season has no matches.
    """
    with st.sidebar:
        st.header("Select a match")
        comps = get_competitions()

        country = st.selectbox("Country", sorted(comps["country_name"].unique()))
        country_rows = comps[comps["country_name"] == country]

        competition_name = st.selectbox(
            "Competition", sorted(country_rows["competition_name"].unique())
        )
        competition_rows = country_rows[country_rows["competition_name"] == competition_name]

        season_name = st.selectbox(
            "Season", sorted(competition_rows["season_name"].unique(), reverse=True)
        )
        comp_row = competition_rows[competition_rows["season_name"] == season_name].iloc[0]
        competition_id = int(comp_row["competition_id"])
        season_id = int(comp_row["season_id"])

        matches = get_matches(competition_id, season_id)
        if matches.empty:
            st.warning("No matches found for this selection.")
            st.stop()

        matches = matches.copy()
        matches["label"] = _match_labels(matches)
        match_choice = st.selectbox("Match (optional)", [RANDOM_LABEL] + matches["label"].tolist())

        if match_choice == RANDOM_LABEL:
            # Remember the random pick per competition+season so it doesn't
            # re-shuffle on every unrelated rerun (e.g. a tab click). The
            # Shuffle button deliberately re-rolls it.
            random_key = f"random_match_{competition_id}_{season_id}"
            if random_key not in st.session_state:
                st.session_state[random_key] = random.choice(matches["match_id"].tolist())
            if st.button("🔀 Shuffle random match"):
                st.session_state[random_key] = random.choice(matches["match_id"].tolist())
            match_id = int(st.session_state[random_key])
        else:
            match_id = int(matches.loc[matches["label"] == match_choice, "match_id"].iloc[0])

        match_row = matches[matches["match_id"] == match_id].iloc[0]
        return Selection(
            competition_id=competition_id,
            season_id=season_id,
            match_id=match_id,
            label=str(match_row["label"]),
            home_team=str(match_row["home_team"]),
            events=get_events(match_id),
        )


def _show(fig: Figure) -> None:
    """Render a figure, then close it.

    pyplot keeps every figure alive until it is closed, and Streamlit
    reruns the whole script on each interaction, so unclosed figures pile
    up in memory over a session.
    """
    st.pyplot(fig)
    plt.close(fig)


def render_shot_map(sel: Selection) -> None:
    _show(plot_shot_map(get_shots(sel.match_id), title="Shots — both teams"))
    st.caption("Bubble size = expected goals (xG). Red = goal.")


def render_xg_timeline(sel: Selection) -> None:
    _show(plot_xg_timeline(get_xg_timeline(sel.match_id), title="Cumulative xG"))
    st.caption(
        "Each step is a shot, rising by that shot's expected goals (xG); "
        "large dots are goals. A team finishing well above its xG line "
        "scored more than its chances suggested."
    )

    shootout = get_shootout(sel.match_id)
    if not shootout.empty:
        st.markdown("#### Penalty shootout")
        st.markdown(shootout_table_html(shootout), unsafe_allow_html=True)
        st.caption("✅ = scored, 🔴 = missed. Hover over a kick to see who took it.")


def render_pass_map(sel: Selection) -> None:
    events = sel.events
    players = sorted(events[events["type"] == "Pass"]["player"].dropna().unique().tolist())
    player_choice = st.selectbox("Player (optional filter)", ["All players"] + players)
    player_filter = None if player_choice == "All players" else player_choice

    passes = get_passes(sel.match_id, player=player_filter)
    _show(plot_pass_map(passes, title=f"Passes — {player_choice}"))
    st.caption("Green = completed pass, red = incomplete.")


def render_pass_network(sel: Selection) -> None:
    columns = st.columns(2)
    for col, team in zip(columns, teams_in_match(sel.match_id)):
        with col:
            st.markdown(f"**{team}**")
            nodes, edges = get_pass_network(sel.match_id, team)
            _show(plot_pass_network(nodes, edges, title=""))
    st.caption(
        "Node position = player's average location on the ball; node size = "
        "passes made; line thickness = passes between that pair. Only passes "
        "before the team's first substitution are used, to keep the shape "
        "based on one settled XI."
    )


def render_heatmap(sel: Selection) -> None:
    _show(plot_heatmap(sel.events, title="Touch density — both teams"))


def render_match_details(sel: Selection) -> None:
    teams = teams_in_match(sel.match_id)
    managers = get_managers(sel.competition_id, sel.season_id, sel.match_id)
    starting_xi = get_starting_xi(sel.match_id)
    subs = get_substitutions(sel.match_id)

    st.markdown("### Starting XI")
    for col, team in zip(st.columns(2), teams):
        with col:
            st.markdown(f"**{team}**")
            manager_key = "home" if team == sel.home_team else "away"
            st.caption(f"Manager: {managers.get(manager_key, 'Not available')}")
            xi = starting_xi.get(team)
            if xi is None or xi.empty:
                st.write("Starting XI not available for this match.")
            else:
                st.dataframe(
                    xi.rename(columns={"player": "Player", "jersey_number": "#", "position": "Position"}),
                    hide_index=True,
                    use_container_width=True,
                )

    st.markdown("### Substitution timeline")
    if subs.empty:
        st.write("No substitutions recorded for this match.")
        return

    display_subs = subs.copy()
    display_subs["Time"] = display_subs["minute"].astype(str) + "'"
    for col, team in zip(st.columns(2), teams):
        with col:
            st.markdown(f"**{team}**")
            team_subs = display_subs[display_subs["team"] == team].rename(
                columns={"player_off": "Off", "player_on": "On"}
            )[["Time", "Off", "On"]]
            if team_subs.empty:
                st.write("No substitutions for this team.")
            else:
                st.dataframe(team_subs, hide_index=True, use_container_width=True)


def render_about() -> None:
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


def main() -> None:
    st.set_page_config(page_title="Pitchside Analytics", page_icon="⚽", layout="wide")
    apply_custom_style()
    render_header()

    sel = render_sidebar()
    st.subheader(sel.label)

    renderers = [
        lambda: render_shot_map(sel),
        lambda: render_xg_timeline(sel),
        lambda: render_pass_map(sel),
        lambda: render_pass_network(sel),
        lambda: render_heatmap(sel),
        lambda: render_match_details(sel),
        render_about,
    ]
    for tab, render in zip(st.tabs(TAB_LABELS), renderers):
        with tab:
            render()


main()
