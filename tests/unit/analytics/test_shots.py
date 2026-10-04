"""
Unit tests for pitchside.analytics.shots: shots, xG timeline, shootouts.

The functions are pure, so each test passes frames straight in: no
mocking, no data source.
"""

import pandas as pd
import pytest

from pitchside.analytics.shots import (
    SHOOTOUT_COLUMNS,
    XG_TIMELINE_COLUMNS,
    match_shots,
    shootout,
    teams,
    xg_timeline,
)


# --- teams -------------------------------------------------------------------

@pytest.mark.unit
def test_teams_returns_sorted_unique_teams(events_frame):
    assert teams(events_frame) == ["Away Team", "Home Team"]


@pytest.mark.unit
def test_teams_empty_when_frame_has_no_team_column():
    assert teams(pd.DataFrame()) == []


# --- match_shots -------------------------------------------------------------

@pytest.mark.unit
def test_match_shots_filters_to_shot_type_only(events_frame):
    shots = match_shots(events_frame)
    assert set(shots["type"]) == {"Shot"}
    assert len(shots) == 2


@pytest.mark.unit
def test_match_shots_filters_by_team(events_frame):
    shots = match_shots(events_frame, team="Away Team")
    assert len(shots) == 1
    assert shots.iloc[0]["player"] == "Player Y"


@pytest.mark.unit
def test_match_shots_excludes_penalty_shootout(shootout_events):
    shots = match_shots(shootout_events)
    assert list(shots["player"]) == ["Player A", "Player X"]


# --- xg_timeline -------------------------------------------------------------

@pytest.mark.unit
def test_xg_timeline_accumulates_xg_per_team(events_frame):
    timeline = xg_timeline(events_frame)

    home = timeline[timeline["team"] == "Home Team"]
    assert list(home["minute"]) == [0.0, 30.25], "Kickoff row, then the 30:15 shot."
    assert list(home["cumulative_xg"]) == pytest.approx([0.0, 0.35])
    assert list(home["is_goal"]) == [False, True]

    away = timeline[timeline["team"] == "Away Team"]
    assert away["cumulative_xg"].iloc[-1] == pytest.approx(0.08)
    assert not away["is_goal"].any()


@pytest.mark.unit
def test_xg_timeline_team_without_shots_gets_flat_line():
    events = pd.DataFrame([
        {"type": "Pass", "team": "Home Team", "player": "Player A", "minute": 5, "second": 0},
        {
            "type": "Shot", "team": "Away Team", "player": "Player Y", "minute": 10, "second": 0,
            "shot_outcome": "Saved", "shot_statsbomb_xg": 0.2,
        },
    ])
    timeline = xg_timeline(events)
    home = timeline[timeline["team"] == "Home Team"]
    assert len(home) == 1
    assert home.iloc[0]["cumulative_xg"] == 0.0


@pytest.mark.unit
def test_xg_timeline_orders_shots_within_the_same_minute_by_second():
    events = pd.DataFrame([
        {"type": "Shot", "team": "Home Team", "player": "Late", "minute": 20, "second": 50,
         "shot_outcome": "Goal", "shot_statsbomb_xg": 0.5},
        {"type": "Shot", "team": "Home Team", "player": "Early", "minute": 20, "second": 5,
         "shot_outcome": "Saved", "shot_statsbomb_xg": 0.1},
    ])
    timeline = xg_timeline(events)
    assert list(timeline["player"].dropna()) == ["Early", "Late"]
    assert list(timeline["cumulative_xg"]) == pytest.approx([0.0, 0.1, 0.6])


@pytest.mark.unit
def test_xg_timeline_no_events_returns_empty_frame_with_expected_columns():
    events = pd.DataFrame(columns=["type", "team", "minute", "second", "player"])
    timeline = xg_timeline(events)
    assert timeline.empty
    assert list(timeline.columns) == XG_TIMELINE_COLUMNS


@pytest.mark.unit
def test_xg_timeline_excludes_penalty_shootout(shootout_events):
    """Shootout kicks aren't chances within the match: including them used
    to push a 1-1 draw to 8+ cumulative xG per team."""
    timeline = xg_timeline(shootout_events)
    totals = timeline.groupby("team")["cumulative_xg"].last()
    assert totals["Home Team"] == pytest.approx(0.30)
    assert totals["Away Team"] == pytest.approx(0.10)
    assert timeline["minute"].max() == 110


@pytest.mark.unit
def test_xg_timeline_treats_missing_xg_as_zero():
    events = pd.DataFrame([
        {"type": "Shot", "team": "Home Team", "player": "P", "minute": 3, "second": 0,
         "shot_outcome": "Blocked", "shot_statsbomb_xg": float("nan")},
    ])
    assert xg_timeline(events)["cumulative_xg"].iloc[-1] == 0.0


# --- shootout ----------------------------------------------------------------

@pytest.mark.unit
def test_shootout_numbers_kicks_per_team_in_order_taken(shootout_events):
    # Add a third kick, listed out of order, to check sorting by event index.
    extra = pd.DataFrame([{
        "type": "Shot", "team": "Home Team", "player": "Player C", "period": 5,
        "minute": 122, "second": 0, "shot_statsbomb_xg": 0.78, "shot_outcome": "Post",
    }])
    events = pd.concat([extra, shootout_events], ignore_index=True)
    events["index"] = [5, 1, 2, 3, 4]
    kicks = shootout(events)
    assert list(kicks["player"]) == ["Player B", "Player Y", "Player C"]
    assert list(kicks["team"]) == ["Home Team", "Away Team", "Home Team"]
    assert list(kicks["kick"]) == [1, 1, 2]
    assert list(kicks["scored"]) == [True, False, False]


@pytest.mark.unit
def test_shootout_empty_when_match_had_none(events_frame):
    kicks = shootout(events_frame)
    assert kicks.empty
    assert list(kicks.columns) == SHOOTOUT_COLUMNS


@pytest.mark.unit
def test_shootout_empty_when_no_period_5_shots(shootout_events):
    regulation_only = shootout_events[shootout_events["period"] != 5]
    assert shootout(regulation_only).empty
