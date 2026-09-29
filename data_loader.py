"""
data_loader.py
Thin wrapper around statsbombpy's free open-data API.

statsbombpy pulls from StatsBomb's public "open-data" GitHub repo, so no
API key is needed, but only certain competitions/seasons are available
(e.g. FIFA World Cup 2018, Women's World Cup, some La Liga/Messi seasons).
See: https://github.com/statsbomb/open-data for what's included.

statsbombpy types its fetchers as returning ``DataFrame | dict`` because a
``fmt`` parameter can switch the output to raw dicts. It is never passed
here, so the result is always a DataFrame; ``typing.cast`` records that
for the type checker without silencing real errors elsewhere.
"""

from functools import lru_cache
from typing import cast

import pandas as pd
from statsbombpy import sb


@lru_cache(maxsize=1)
def get_competitions() -> pd.DataFrame:
    """Return every competition/season in StatsBomb's open data.

    Cached after the first call, since the list doesn't change within a run.

    Returns:
        One row per competition+season, with columns such as
        ``competition_id``, ``season_id``, ``country_name``,
        ``competition_name`` and ``season_name``.
    """
    return cast(pd.DataFrame, sb.competitions())


@lru_cache(maxsize=32)
def get_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    """Return all matches played in a competition/season.

    Returns:
        One row per match, with columns such as ``match_id``,
        ``home_team``, ``away_team``, ``home_score``, ``away_score``,
        ``match_date``, ``home_managers`` and ``away_managers``.
    """
    return cast(pd.DataFrame, sb.matches(competition_id=competition_id, season_id=season_id))


@lru_cache(maxsize=32)
def get_events(match_id: int) -> pd.DataFrame:
    """Return every recorded event (passes, shots, duels, ...) for a match.

    Returns:
        One row per event, with columns such as ``type``, ``team``,
        ``player``, ``location``, ``minute``, plus event-specific columns
        (e.g. ``shot_outcome``, ``pass_recipient``).
    """
    return cast(pd.DataFrame, sb.events(match_id=match_id))


SHOOTOUT_PERIOD = 5


def _match_shots(events: pd.DataFrame) -> pd.DataFrame:
    """Return the shot events from open play and set pieces.

    StatsBomb records each penalty-shootout kick as a Shot in period 5, at
    roughly 0.78 xG apiece. They aren't chances within the match and would
    add several xG to each team, so they are left out.
    """
    shots = events[events["type"] == "Shot"]
    if "period" in shots.columns:
        shots = shots[shots["period"] != SHOOTOUT_PERIOD]
    return shots.copy()


def get_shootout(match_id: int) -> pd.DataFrame:
    """Return a match's penalty shootout kicks, in the order they were taken.

    Returns:
        Columns ``team``, ``kick`` (1-based, counted per team), ``player``
        and ``scored``. Empty (but with those columns) if the match had no
        shootout.
    """
    columns = ["team", "kick", "player", "scored"]
    events = get_events(match_id)
    if "period" not in events.columns:
        return pd.DataFrame(columns=columns)
    kicks = events[(events["type"] == "Shot") & (events["period"] == SHOOTOUT_PERIOD)].copy()
    if kicks.empty:
        return pd.DataFrame(columns=columns)
    # StatsBomb's "index" is the event's position in the match sequence.
    order = "index" if "index" in kicks.columns else ["minute", "second"]
    kicks = kicks.sort_values(order, kind="stable")
    kicks["kick"] = kicks.groupby("team").cumcount() + 1
    kicks["scored"] = kicks["shot_outcome"] == "Goal"
    return kicks[columns].reset_index(drop=True)


def get_shots(match_id: int, team: str | None = None) -> pd.DataFrame:
    """Return a match's shot events (excluding any penalty shootout),
    optionally for one team only."""
    events = get_events(match_id)
    shots = _match_shots(events)
    if team:
        shots = shots[shots["team"] == team]
    return shots


def get_passes(match_id: int, team: str | None = None, player: str | None = None) -> pd.DataFrame:
    """Return a match's pass events, optionally filtered by team and/or player.

    Passes without a start or end location are dropped, since they can't
    be plotted.
    """
    events = get_events(match_id)
    passes = events[events["type"] == "Pass"].copy()
    if team:
        passes = passes[passes["team"] == team]
    if player:
        passes = passes[passes["player"] == player]
    return passes.dropna(subset=["location", "pass_end_location"])


def teams_in_match(match_id: int) -> list[str]:
    """Return the sorted team names that appear in a match's event data."""
    events = get_events(match_id)
    return sorted(events["team"].dropna().unique().tolist())


@lru_cache(maxsize=32)
def get_lineups(match_id: int) -> dict[str, pd.DataFrame]:
    """Return full squad lineups for both teams in a match.

    Returns:
        Dict keyed by team name. Each DataFrame has one row per player,
        with ``player_name``, ``jersey_number`` and ``positions`` (a list
        of dicts with ``position`` and ``start_reason``, e.g.
        "Starting XI" or "Substitution - On").
    """
    return cast(dict[str, pd.DataFrame], sb.lineups(match_id=match_id))


def get_starting_xi(match_id: int) -> dict[str, pd.DataFrame]:
    """Return each team's starting XI and the position each player started in.

    Returns:
        Dict keyed by team name. Each DataFrame has columns ``player``,
        ``jersey_number`` and ``position``, sorted by jersey number.
    """
    lineups = get_lineups(match_id)
    result: dict[str, pd.DataFrame] = {}
    for team, df in lineups.items():
        rows: list[dict[str, object]] = []
        for _, row in df.iterrows():
            positions = row.get("positions") or []
            starters = [p for p in positions if p.get("start_reason") == "Starting XI"]
            if starters:
                rows.append({
                    "player": row["player_name"],
                    "jersey_number": row["jersey_number"],
                    "position": starters[0].get("position", ""),
                })
        xi_df = pd.DataFrame(rows, columns=["player", "jersey_number", "position"])
        if not xi_df.empty:
            xi_df = xi_df.sort_values("jersey_number").reset_index(drop=True)
        result[team] = xi_df
    return result


def get_substitutions(match_id: int) -> pd.DataFrame:
    """Return a match's substitutions as a timeline.

    Returns:
        Columns ``team``, ``minute``, ``second``, ``player_off``,
        ``player_on``, one row per substitution sorted by time. Empty (but
        with those columns) if none were recorded.
    """
    events = get_events(match_id)
    subs = events[events["type"] == "Substitution"].copy()
    if subs.empty:
        return pd.DataFrame(columns=["team", "minute", "second", "player_off", "player_on"])
    sort_cols = ["minute", "second"] if "second" in subs.columns else ["minute"]
    subs = subs.sort_values(sort_cols)
    return pd.DataFrame({
        "team": subs["team"].values,
        "minute": subs["minute"].values,
        "second": subs["second"].values if "second" in subs.columns else 0,
        "player_off": subs["player"].values,
        "player_on": subs["substitution_replacement"].values
        if "substitution_replacement" in subs.columns else "Unknown",
    }).reset_index(drop=True)


def get_managers(competition_id: int, season_id: int, match_id: int) -> dict[str, str]:
    """Return the home and away managers for a match.

    Returns:
        ``{"home": ..., "away": ...}``, with "Not available" wherever the
        dataset has no manager recorded.
    """
    matches = get_matches(competition_id, season_id)
    row = matches[matches["match_id"] == match_id]
    if row.empty:
        return {"home": "Not available", "away": "Not available"}
    row = row.iloc[0]

    def _manager(col: str) -> str:
        # pandas stores a missing manager as NaN (truthy), not None, so a
        # plain `or "Not available"` fallback would render the string "nan".
        value = row.get(col)
        return "Not available" if value is None or pd.isna(value) or value == "" else str(value)

    return {"home": _manager("home_managers"), "away": _manager("away_managers")}


def get_pass_network(match_id: int, team: str, until_first_sub: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    events = get_events(match_id)
    passes = events[(events["type"] == "Pass") & (events["team"] == team)].copy()
    passes = passes.dropna(subset=["location", "player"])

    if until_first_sub:
        subs = get_substitutions(match_id)
        team_subs = subs[subs["team"] == team]
        if not team_subs.empty:
            passes = passes[passes["minute"] < team_subs["minute"].min()]

    node_cols = ["player", "x", "y", "passes"]
    edge_cols = ["player", "pass_recipient", "count", "x1", "y1", "x2", "y2"]
    if passes.empty:
        return pd.DataFrame(columns=node_cols), pd.DataFrame(columns=edge_cols)

    passes["x"] = passes["location"].apply(lambda loc: loc[0])
    passes["y"] = passes["location"].apply(lambda loc: loc[1])

    nodes = (
        passes.groupby("player")
        .agg(x=("x", "mean"), y=("y", "mean"), passes=("x", "count"))
        .reset_index()
    )

    completed = passes.copy()
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

    return nodes, edges


def get_xg_timeline(match_id: int) -> pd.DataFrame:
    """Return each team's cumulative expected goals (xG) shot by shot.

    Every team gets a starting row at minute 0 with 0 xG, so a team that
    never shot still produces a flat line. Minutes include seconds as a
    fraction, so two shots in the same minute stay in order. Penalty
    shootout kicks are excluded (see ``_match_shots``).

    Returns:
        Columns ``team``, ``minute`` (float), ``xg`` (that shot's xG),
        ``cumulative_xg``, ``is_goal`` and ``player``, sorted by team then
        time.
    """
    events = get_events(match_id)
    teams = sorted(events["team"].dropna().unique().tolist())
    shots = _match_shots(events)

    columns =["team", "minute", "xg", "cumulative_xg", "is_goal", "player"]
    if not teams:
        return pd.DataFrame(columns=columns)

    if not shots.empty:
        seconds = shots["second"].fillna(0) if "second" in shots.columns else 0
        shots["minute"] = shots["minute"].astype(float) + seconds / 60
        shots["xg"] = (
            shots["shot_statsbomb_xg"].fillna(0.0).astype(float)
            if "shot_statsbomb_xg" in shots.columns else 0.0
        )
        shots["is_goal"] = shots["shot_outcome"] == "Goal"
        shots = shots[["team", "minute", "xg", "is_goal", "player"]]

    kickoff = pd.DataFrame({
        "team": teams, "minute": 0.0, "xg": 0.0, "is_goal": False, "player": None,
    })
    frames = [kickoff] if shots.empty else [kickoff, shots]
    timeline = pd.concat(frames, ignore_index=True)
    timeline = timeline.sort_values(["team", "minute"], kind="stable").reset_index(drop=True)
    timeline["cumulative_xg"] = timeline.groupby("team")["xg"].cumsum()
    return timeline[columns]
