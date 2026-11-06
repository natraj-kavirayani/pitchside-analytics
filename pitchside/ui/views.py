"""
The tabs, as a registry.

Each ``View`` is a tab label, the tab's accent colour and the function
that renders it. The app builds its tabs, the theme builds its tab
colours and the tests enumerate the tabs from ``VIEWS``, so adding a view
is one entry here with nothing else to keep in sync.
"""

from collections.abc import Callable
from dataclasses import dataclass

import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.figure import Figure

from pitchside.analytics.lineups import jersey_labels
from pitchside.service import MatchRef, MatchService
from pitchside.viz.charts import (
    plot_heatmap,
    plot_pass_map,
    plot_pass_network,
    plot_shot_map,
    plot_xg_timeline,
)
from pitchside.viz.tables import shootout_table_html

ALL_PLAYERS = "All players"


@dataclass(frozen=True)
class MatchContext:
    """What every view needs: the data service and the selected match."""

    service: MatchService
    match: MatchRef


@dataclass(frozen=True)
class View:
    label: str
    accent: str
    render: Callable[[MatchContext], None]


def _show(fig: Figure) -> None:
    """Render a figure, then close it.

    pyplot keeps every figure alive until it is closed, and Streamlit
    reruns the whole script on each interaction, so unclosed figures pile
    up in memory over a session.
    """
    st.pyplot(fig)
    plt.close(fig)


def render_shot_map(ctx: MatchContext) -> None:
    _show(plot_shot_map(ctx.service.shots(ctx.match.match_id), title="Shots — both teams"))
    st.caption("Bubble size = expected goals (xG). Red = goal.")


def render_xg_timeline(ctx: MatchContext) -> None:
    _show(plot_xg_timeline(ctx.service.xg_timeline(ctx.match.match_id), title="Cumulative xG"))
    st.caption(
        "Each step is a shot, rising by that shot's expected goals (xG); "
        "large dots are goals. A team finishing well above its xG line "
        "scored more than its chances suggested."
    )

    shootout = ctx.service.shootout(ctx.match.match_id)
    if not shootout.empty:
        st.markdown("#### Penalty shootout")
        st.markdown(shootout_table_html(shootout), unsafe_allow_html=True)
        st.caption("✅ = scored, 🔴 = missed. Hover over a kick to see who took it.")


def render_pass_map(ctx: MatchContext) -> None:
    match_id = ctx.match.match_id
    player_choice = st.selectbox("Player (optional filter)", [ALL_PLAYERS, *ctx.service.passers(match_id)])
    player = None if player_choice == ALL_PLAYERS else player_choice
    _show(plot_pass_map(ctx.service.passes(match_id, player=player), title=f"Passes — {player_choice}"))
    st.caption("Green = completed pass, red = incomplete.")


def render_pass_network(ctx: MatchContext) -> None:
    columns = st.columns(2)
    for col, team in zip(columns, ctx.service.teams(ctx.match.match_id)):
        with col:
            st.markdown(f"**{team}**")
            nodes, edges = ctx.service.pass_network(ctx.match.match_id, team)
            _show(plot_pass_network(nodes, edges, title=""))
    st.caption(
        "Node position = player's average location on the ball; node size = "
        "passes made; line thickness = passes between that pair. Only passes "
        "before the team's first substitution are used, to keep the shape "
        "based on one settled XI."
    )


def render_heatmap(ctx: MatchContext) -> None:
    _show(plot_heatmap(ctx.service.events(ctx.match.match_id), title="Touch density — both teams"))


def render_match_details(ctx: MatchContext) -> None:
    match, service = ctx.match, ctx.service
    teams = service.teams(match.match_id)
    managers = service.managers(match)
    starting_xi = service.starting_xi(match.match_id)
    subs = service.substitutions(match.match_id)

    st.markdown("### Starting XI")
    for col, team in zip(st.columns(2), teams):
        with col:
            st.markdown(f"**{team}**")
            manager_key = "home" if team == match.home_team else "away"
            st.caption(f"Manager: {managers[manager_key]}")
            xi = starting_xi.get(team)
            if xi is None or xi.empty:
                st.write("Starting XI not available for this match.")
            else:
                xi = xi.assign(jersey_number=jersey_labels(xi["jersey_number"]))
                st.dataframe(
                    xi.rename(columns={"player": "Player", "jersey_number": "#", "position": "Position"}),
                    hide_index=True,
                    width="stretch",
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
                st.dataframe(team_subs, hide_index=True, width="stretch")


VIEWS: tuple[View, ...] = (
    View("Shot map", "#ef4444", render_shot_map),
    View("xG timeline", "#3b82f6", render_xg_timeline),
    View("Pass map", "#22c55e", render_pass_map),
    View("Pass network", "#f59e0b", render_pass_network),
    View("Touch heatmap", "#a855f7", render_heatmap),
    View("Match details", "#ec4899", render_match_details),
)
