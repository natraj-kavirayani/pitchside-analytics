"""Headline numbers for each team in a match."""

import pandas as pd

from pitchside.analytics.shots import match_shots, teams

# StatsBomb outcomes for a shot that would have gone in without the keeper.
ON_TARGET = frozenset({"Goal", "Saved", "Saved To Post"})
SUMMARY_COLUMNS = ["team", "xg", "shots", "on_target", "passes", "pass_completion"]


def team_summary(events: pd.DataFrame) -> pd.DataFrame:
    """Return xG, shots, shots on target, passes and pass completion per team.

    Penalty shootout kicks are not shots in the match, so they are left
    out (see ``match_shots``). Pass completion is a percentage of the
    team's passes, or 0 for a team that made none.

    Returns:
        One row per team, sorted by team name, with ``SUMMARY_COLUMNS``.
    """
    shots = match_shots(events)
    pass_events = events[events["type"] == "Pass"]
    rows = []
    for team in teams(events):
        team_shots = shots[shots["team"] == team]
        team_passes = pass_events[pass_events["team"] == team]
        completed = (
            int(team_passes["pass_outcome"].isna().sum())
            if "pass_outcome" in team_passes.columns else len(team_passes)
        )
        xg = (
            float(team_shots["shot_statsbomb_xg"].fillna(0.0).sum())
            if "shot_statsbomb_xg" in team_shots.columns else 0.0
        )
        rows.append({
            "team": team,
            "xg": xg,
            "shots": len(team_shots),
            "on_target": int(team_shots["shot_outcome"].isin(ON_TARGET).sum()) if len(team_shots) else 0,
            "passes": len(team_passes),
            "pass_completion": 100.0 * completed / len(team_passes) if len(team_passes) else 0.0,
        })
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
