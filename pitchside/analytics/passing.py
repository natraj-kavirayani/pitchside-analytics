"""Passes and pass networks."""

import pandas as pd

from pitchside.analytics.lineups import substitutions

NODE_COLUMNS = ["player", "x", "y", "passes"]
EDGE_COLUMNS = ["player1", "player2", "count", "x1", "y1", "x2", "y2"]
# Pairs that completed fewer passes than this (both directions together)
# get no line: one-off passes clutter the chart without showing a link.
MIN_PAIR_PASSES = 3


def passes(events: pd.DataFrame, team: str | None = None, player: str | None = None) -> pd.DataFrame:
    """Return a match's pass events, optionally filtered by team and/or player.

    Passes without a start or end location are dropped, since they can't
    be plotted.
    """
    result = events[events["type"] == "Pass"].copy()
    if team:
        result = result[result["team"] == team]
    if player:
        result = result[result["player"] == player]
    return result.dropna(subset=["location", "pass_end_location"])


def passers(events: pd.DataFrame) -> list[str]:
    """Return the sorted names of every player who made a pass."""
    return sorted(events.loc[events["type"] == "Pass", "player"].dropna().unique().tolist())


def pass_network(
    events: pd.DataFrame, team: str, until_first_sub: bool = True,
    min_passes: int = MIN_PAIR_PASSES,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the data behind a team's pass network.

    Each player's node sits at the average location of the passes they
    made (not of every touch: receptions, carries and so on aren't
    counted). Each edge joins a pair of players and counts the completed
    passes between them in both directions, so A->B and B->A make one
    line; pairs with fewer than ``min_passes`` get none. By default only
    passes before the team's first substitution are used - the standard
    convention, so the shape reflects one settled XI.

    Returns:
        ``(nodes, edges)``. nodes: ``player``, ``x``, ``y``, ``passes``.
        edges: ``player1``, ``player2`` (in alphabetical order), ``count``,
        ``x1``, ``y1``, ``x2``, ``y2`` (line between the two players'
        nodes).
    """
    team_passes = events[(events["type"] == "Pass") & (events["team"] == team)].copy()
    team_passes = team_passes.dropna(subset=["location", "player"])

    if until_first_sub:
        subs = substitutions(events)
        team_subs = subs[subs["team"] == team]
        if not team_subs.empty:
            team_passes = team_passes[team_passes["minute"] < team_subs["minute"].min()]

    if team_passes.empty:
        return pd.DataFrame(columns=NODE_COLUMNS), pd.DataFrame(columns=EDGE_COLUMNS)

    team_passes["x"] = team_passes["location"].apply(lambda loc: loc[0])
    team_passes["y"] = team_passes["location"].apply(lambda loc: loc[1])

    nodes = (
        team_passes.groupby("player")
        .agg(x=("x", "mean"), y=("y", "mean"), passes=("x", "count"))
        .reset_index()
    )

    completed = team_passes
    if "pass_outcome" in completed.columns:
        completed = completed[completed["pass_outcome"].isna()]  # NaN outcome = completed
    completed = completed.dropna(subset=["pass_recipient"])
    completed = completed[completed["player"] != completed["pass_recipient"]]  # no pair to link

    pairs = pd.DataFrame({
        "player1": completed[["player", "pass_recipient"]].min(axis=1),
        "player2": completed[["player", "pass_recipient"]].max(axis=1),
    })
    edges = pairs.groupby(["player1", "player2"]).size().reset_index(name="count")
    edges = edges[edges["count"] >= min_passes].copy()
    pos_lookup_x = nodes.set_index("player")["x"]
    pos_lookup_y = nodes.set_index("player")["y"]
    edges["x1"] = edges["player1"].map(pos_lookup_x)
    edges["y1"] = edges["player1"].map(pos_lookup_y)
    edges["x2"] = edges["player2"].map(pos_lookup_x)
    edges["y2"] = edges["player2"].map(pos_lookup_y)
    edges = edges.dropna(subset=["x1", "y1", "x2", "y2"]).reset_index(drop=True)

    return nodes, edges[EDGE_COLUMNS]
