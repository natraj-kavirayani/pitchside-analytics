"""
The columns the app relies on from each kind of StatsBomb frame.

This is the data contract between the data sources and the rest of the
app. The contract tests check both the live StatsBomb API and the offline
sample source against it, so the sample can never drift into a shape the
real data doesn't have, and an upstream rename shows up as one precise
failure instead of a broken chart.

Event columns that only exist on some event types (``shot_*``, ``pass_*``,
``substitution_*``) are listed separately: statsbombpy only creates a
column when at least one event in the match has it.
"""

import pandas as pd

COMPETITION_COLUMNS = frozenset({
    "competition_id", "season_id", "country_name", "competition_name", "season_name",
})

MATCH_COLUMNS = frozenset({
    "match_id", "home_team", "away_team", "home_score", "away_score", "match_date",
    "home_managers", "away_managers",
})

EVENT_COLUMNS = frozenset({
    "index", "period", "minute", "second", "type", "team", "player", "location",
})

SHOT_COLUMNS = frozenset({"shot_outcome", "shot_statsbomb_xg"})
PASS_COLUMNS = frozenset({"pass_end_location", "pass_outcome", "pass_recipient"})
SUBSTITUTION_COLUMNS = frozenset({"substitution_replacement"})

LINEUP_COLUMNS = frozenset({"player_name", "jersey_number", "positions"})


def missing_columns(frame: pd.DataFrame, required: frozenset[str]) -> set[str]:
    """Return the required columns that ``frame`` lacks (empty if none)."""
    return set(required) - set(frame.columns)


def event_contract(events: pd.DataFrame) -> frozenset[str]:
    """Return the columns ``events`` must have, given which event types it contains."""
    required = set(EVENT_COLUMNS)
    types = set(events["type"].dropna()) if "type" in events.columns else set()
    if "Shot" in types:
        required |= SHOT_COLUMNS
    if "Pass" in types:
        required |= PASS_COLUMNS
    if "Substitution" in types:
        required |= SUBSTITUTION_COLUMNS
    return frozenset(required)
