"""Unit tests for pitchside.analytics.lineups: XIs, substitutions, managers."""

import pandas as pd
import pytest

from pitchside.analytics.lineups import (
    SUBSTITUTION_COLUMNS,
    XI_COLUMNS,
    managers,
    starting_xi,
    substitutions,
)


# --- starting_xi -------------------------------------------------------------

@pytest.mark.unit
def test_starting_xi_excludes_non_starters(lineups_dict):
    xi = starting_xi(lineups_dict)

    home = xi["Home Team"]
    assert len(home) == 2, "Player D has no Starting XI entry and must be excluded."
    assert "Player D" not in home["player"].values
    assert list(home["jersey_number"]) == [9, 10]

    away = xi["Away Team"]
    assert len(away) == 1
    assert away.iloc[0]["player"] == "Player X"


@pytest.mark.unit
def test_starting_xi_handles_team_with_no_starters():
    lineups = {
        "Home Team": pd.DataFrame([
            {"player_name": "Sub Only", "jersey_number": 22, "positions": []},
        ]),
    }
    xi = starting_xi(lineups)
    assert xi["Home Team"].empty
    assert list(xi["Home Team"].columns) == XI_COLUMNS


@pytest.mark.unit
def test_starting_xi_uses_the_starting_position_not_a_later_one():
    lineups = {"T": pd.DataFrame([{
        "player_name": "Moved", "jersey_number": 4,
        "positions": [
            {"start_reason": "Starting XI", "position": "Left Back"},
            {"start_reason": "Tactical Shift", "position": "Left Wing"},
        ],
    }])}
    assert starting_xi(lineups)["T"].iloc[0]["position"] == "Left Back"


# --- substitutions -----------------------------------------------------------

@pytest.mark.unit
def test_substitutions_empty():
    empty_events = pd.DataFrame(columns=["type", "team", "minute", "second", "player"])
    subs = substitutions(empty_events)
    assert subs.empty
    assert list(subs.columns) == SUBSTITUTION_COLUMNS


@pytest.mark.unit
def test_substitutions_sorted_by_time_both_teams():
    events = pd.DataFrame([
        {
            "type": "Substitution", "team": "Away Team", "player": "Player X",
            "substitution_replacement": "Player Z", "minute": 70, "second": 0,
        },
        {
            "type": "Substitution", "team": "Home Team", "player": "Player A",
            "substitution_replacement": "Player C", "minute": 60, "second": 30,
        },
        {
            "type": "Pass", "team": "Home Team", "player": "Player B",
            "minute": 10, "second": 0,
        },
    ])
    subs = substitutions(events)
    assert len(subs) == 2
    # Sorted by minute ascending, so the 60' sub comes before the 70' one.
    assert subs.iloc[0][["team", "player_off", "player_on"]].tolist() == ["Home Team", "Player A", "Player C"]
    assert subs.iloc[1]["team"] == "Away Team"


@pytest.mark.unit
def test_substitutions_defaults_missing_columns():
    # No "second" or "substitution_replacement" column at all.
    events = pd.DataFrame([
        {"type": "Substitution", "team": "Home Team", "player": "Player A", "minute": 60},
    ])
    subs = substitutions(events)
    assert subs.iloc[0]["second"] == 0
    assert subs.iloc[0]["player_on"] == "Unknown"


# --- managers ----------------------------------------------------------------

@pytest.mark.unit
def test_managers_found(matches_frame):
    assert managers(matches_frame, 12345) == {"home": "Home Manager", "away": "Away Manager"}


@pytest.mark.unit
def test_managers_defaults_missing_manager_to_not_available(matches_frame):
    # match_id 67890 has home_managers=None in the fixture.
    assert managers(matches_frame, 67890) == {"home": "Not available", "away": "Third Manager"}


@pytest.mark.unit
@pytest.mark.parametrize("missing", [None, float("nan"), ""])
def test_managers_never_shows_nan_or_blank(matches_frame, missing):
    frame = matches_frame.copy()
    frame["away_managers"] = frame["away_managers"].astype(object)
    frame.loc[0, "away_managers"] = missing
    assert managers(frame, 12345)["away"] == "Not available"


@pytest.mark.unit
def test_managers_match_not_found(matches_frame):
    assert managers(matches_frame, 99999) == {"home": "Not available", "away": "Not available"}
