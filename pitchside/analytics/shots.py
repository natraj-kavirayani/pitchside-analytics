"""Shots, expected goals (xG) and penalty shootouts."""

import pandas as pd

SHOOTOUT_PERIOD = 5
SHOOTOUT_COLUMNS = ["team", "kick", "player", "scored"]
XG_TIMELINE_COLUMNS = ["team", "minute", "xg", "cumulative_xg", "is_goal", "player"]


def teams(events: pd.DataFrame) -> list[str]:
    """Return the sorted team names that appear in a match's events."""
    if "team" not in events.columns:
        return []
    return sorted(events["team"].dropna().unique().tolist())


def match_shots(events: pd.DataFrame, team: str | None = None) -> pd.DataFrame:
    """Return the shot events from open play and set pieces, optionally
    for one team only.

    StatsBomb records each penalty-shootout kick as a Shot in period 5, at
    roughly 0.78 xG apiece. They aren't chances within the match and would
    add several xG to each team, so they are left out.
    """
    shots = events[events["type"] == "Shot"]
    if "period" in shots.columns:
        shots = shots[shots["period"] != SHOOTOUT_PERIOD]
    if team:
        shots = shots[shots["team"] == team]
    return shots.copy()


def shootout(events: pd.DataFrame) -> pd.DataFrame:
    """Return a match's penalty shootout kicks, in the order they were taken.

    Returns:
        Columns ``team``, ``kick`` (1-based, counted per team), ``player``
        and ``scored``. Empty (but with those columns) if the match had no
        shootout.
    """
    if "period" not in events.columns:
        return pd.DataFrame(columns=SHOOTOUT_COLUMNS)
    kicks = events[(events["type"] == "Shot") & (events["period"] == SHOOTOUT_PERIOD)].copy()
    if kicks.empty:
        return pd.DataFrame(columns=SHOOTOUT_COLUMNS)
    # StatsBomb's "index" is the event's position in the match sequence.
    order = "index" if "index" in kicks.columns else ["minute", "second"]
    kicks = kicks.sort_values(order, kind="stable")
    kicks["kick"] = kicks.groupby("team").cumcount() + 1
    kicks["scored"] = kicks["shot_outcome"] == "Goal"
    return kicks[SHOOTOUT_COLUMNS].reset_index(drop=True)


def xg_timeline(events: pd.DataFrame) -> pd.DataFrame:
    """Return each team's cumulative expected goals (xG) shot by shot.

    Every team gets a starting row at minute 0 with 0 xG, so a team that
    never shot still produces a flat line. Minutes include seconds as a
    fraction, so two shots in the same minute stay in order. Penalty
    shootout kicks are excluded (see ``match_shots``).

    Returns:
        Columns ``team``, ``minute`` (float), ``xg`` (that shot's xG),
        ``cumulative_xg``, ``is_goal`` and ``player``, sorted by team then
        time.
    """
    match_teams = teams(events)
    if not match_teams:
        return pd.DataFrame(columns=XG_TIMELINE_COLUMNS)
    shots = match_shots(events)

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
        "team": match_teams, "minute": 0.0, "xg": 0.0, "is_goal": False, "player": None,
    })
    frames = [kickoff] if shots.empty else [kickoff, shots]
    timeline = pd.concat(frames, ignore_index=True)
    timeline = timeline.sort_values(["team", "minute"], kind="stable").reset_index(drop=True)
    timeline["cumulative_xg"] = timeline.groupby("team")["xg"].cumsum()
    return timeline[XG_TIMELINE_COLUMNS]
