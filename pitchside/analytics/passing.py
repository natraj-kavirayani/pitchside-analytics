"""Passes and pass networks."""

import pandas as pd

from pitchside.analytics.lineups import substitutions

NODE_COLUMNS = ["player", "x", "y", "passes"]
EDGE_COLUMNS = ["player", "pass_recipient", "count", "x1", "y1", "x2", "y2"]


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
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the data behind a team's pass network.

    Each player's node sits at the average location of the passes they
    made (which doubles as their average position), and each edge counts
    completed passes between a pair of players. By default only passes
    before the team's first substitution are used - the standard
    convention, so the shape reflects one settled XI.

    Returns:
        ``(nodes, edges)``. nodes: ``player``, ``x``, ``y``, ``passes``.
        edges: ``player``, ``pass_recipient``, ``count``, ``x1``, ``y1``,
        ``x2``, ``y2`` (line from passer's to recipient's average position).
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

    edges = (
        completed.groupby(["player", "pass_recipient"])
        .size()
        .reset_index(name="count")
    )
    pos_lookup_x = nodes.set_index("player")["x"]
    pos_lookup_y = nodes.set_index("player")["y"]
    edges["x1"] = edges["player"].map(pos_lookup_x)
    edges["y1"] = edges["player"].map(pos_lookup_y)
    edges["x2"] = edges["pass_recipient"].map(pos_lookup_x)
    edges["y2"] = edges["pass_recipient"].map(pos_lookup_y)
    edges = edges.dropna(subset=["x1", "y1", "x2", "y2"]).reset_index(drop=True)

    return nodes, edges[EDGE_COLUMNS]
