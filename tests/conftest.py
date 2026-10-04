"""
Shared fixtures for the whole test suite.

All StatsBomb-shaped data here is hand-built. Tests hand it to the code
under test directly (analytics functions take frames) or through an
``InMemorySource`` (the service and the app take a source), so nothing
needs patching and no cache can leak between tests: each test builds its
own source.
"""

import pandas as pd
import pytest

from pitchside.data.source import InMemorySource
from pitchside.service import MatchService

MATCH_ID = 12345


@pytest.fixture
def competitions_frame() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "competition_id": 2,
            "season_id": 44,
            "country_name": "England",
            "competition_name": "Premier League",
            "season_name": "2015/2016",
        },
        {
            "competition_id": 11,
            "season_id": 90,
            "country_name": "Spain",
            "competition_name": "La Liga",
            "season_name": "2020/2021",
        },
    ])


@pytest.fixture
def matches_frame() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "match_id": MATCH_ID,
            "home_team": "Home Team",
            "away_team": "Away Team",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2016-05-01",
            "home_managers": "Home Manager",
            "away_managers": "Away Manager",
        },
        {
            "match_id": 67890,
            "home_team": "Away Team",
            "away_team": "Third Team",
            "home_score": 0,
            "away_score": 0,
            "match_date": "2016-05-08",
            "home_managers": None,
            "away_managers": "Third Manager",
        },
    ])


@pytest.fixture
def events_frame() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "type": "Pass",
            "team": "Home Team",
            "player": "Player A",
            "location": [10.0, 20.0],
            "pass_end_location": [30.0, 40.0],
            "pass_outcome": float("nan"),
            "pass_recipient": "Player B",
            "minute": 15,
            "second": 10,
        },
        {
            "type": "Pass",
            "team": "Home Team",
            "player": "Player B",
            "location": [30.0, 40.0],
            "pass_end_location": [50.0, 50.0],
            "pass_outcome": "Incomplete",
            "pass_recipient": "Player A",
            "minute": 25,
            "second": 0,
        },
        {
            "type": "Substitution",
            "team": "Home Team",
            "player": "Player A",
            "substitution_replacement": "Player C",
            "minute": 60,
            "second": 0,
        },
        {
            "type": "Pass",
            "team": "Home Team",
            "player": "Player C",
            "location": [50.0, 50.0],
            "pass_end_location": [70.0, 70.0],
            "pass_outcome": float("nan"),
            "pass_recipient": "Player B",
            "minute": 70,
            "second": 0,
        },
        {
            "type": "Shot",
            "team": "Home Team",
            "player": "Player B",
            "location": [100.0, 40.0],
            "shot_outcome": "Goal",
            "shot_statsbomb_xg": 0.35,
            "minute": 30,
            "second": 15,
        },
        {
            "type": "Pass",
            "team": "Away Team",
            "player": "Player X",
            "location": [15.0, 25.0],
            "pass_end_location": [35.0, 45.0],
            "pass_outcome": float("nan"),
            "pass_recipient": "Player Y",
            "minute": 12,
            "second": 0,
        },
        {
            "type": "Shot",
            "team": "Away Team",
            "player": "Player Y",
            "location": [95.0, 38.0],
            "shot_outcome": "Off T",
            "shot_statsbomb_xg": 0.08,
            "minute": 40,
            "second": 0,
        },
    ])


@pytest.fixture
def lineups_dict() -> dict[str, pd.DataFrame]:
    # Mirrors the shape of sb.lineups(): one DataFrame per team, each player
    # carrying a "positions" list. Player D has no "Starting XI" entry, so
    # starting_xi() must leave them out.
    home_df = pd.DataFrame([
        {
            "player_name": "Player A",
            "jersey_number": 10,
            "positions": [{"start_reason": "Starting XI", "position": "Center Midfield"}],
        },
        {
            "player_name": "Player B",
            "jersey_number": 9,
            "positions": [{"start_reason": "Starting XI", "position": "Center Forward"}],
        },
        {
            "player_name": "Player D",
            "jersey_number": 22,
            "positions": [],
        },
    ])
    away_df = pd.DataFrame([
        {
            "player_name": "Player X",
            "jersey_number": 7,
            "positions": [{"start_reason": "Starting XI", "position": "Right Wing"}],
        },
    ])
    return {"Home Team": home_df, "Away Team": away_df}


@pytest.fixture
def shootout_events() -> pd.DataFrame:
    """A 1-1 draw after extra time, followed by a two-kick shootout (period 5)."""
    def shot(team, player, period, minute, xg, outcome):
        return {"type": "Shot", "team": team, "player": player, "period": period,
                "minute": minute, "second": 0, "shot_statsbomb_xg": xg, "shot_outcome": outcome,
                "shot_type": "Penalty" if period == 5 else "Open Play"}
    return pd.DataFrame([
        shot("Home Team", "Player A", 1, 20, 0.30, "Goal"),
        shot("Away Team", "Player X", 4, 110, 0.10, "Goal"),
        shot("Home Team", "Player B", 5, 121, 0.78, "Goal"),
        shot("Away Team", "Player Y", 5, 121, 0.78, "Saved"),
    ])


@pytest.fixture
def frames_source(competitions_frame, matches_frame, events_frame, lineups_dict) -> InMemorySource:
    """The frames above as a data source. Both competitions list the same
    two matches; only match 12345 has events and lineups."""
    return InMemorySource(
        competitions=competitions_frame,
        matches={(2, 44): matches_frame, (11, 90): matches_frame},
        events={MATCH_ID: events_frame},
        lineups={MATCH_ID: lineups_dict},
    )


@pytest.fixture
def frames_service(frames_source) -> MatchService:
    return MatchService(frames_source, label="test frames")
