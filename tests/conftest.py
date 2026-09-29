"""
Shared fixtures for the whole test suite.

All StatsBomb-shaped data here is hand-built and mocked - no test in this
project makes a network call to StatsBomb's open-data GitHub repository.
See tests/unit, tests/component, tests/e2e for how these fixtures are used.
"""

import pandas as pd
import pytest

import data_loader


@pytest.fixture(autouse=True)
def clear_data_loader_caches():
    # data_loader's fetchers are wrapped in lru_cache, which persists across
    # tests in the same process. Clear before and after every test so a
    # mocked return value from one test can never leak into another.
    data_loader.get_competitions.cache_clear()
    data_loader.get_matches.cache_clear()
    data_loader.get_events.cache_clear()
    data_loader.get_lineups.cache_clear()
    yield
    data_loader.get_competitions.cache_clear()
    data_loader.get_matches.cache_clear()
    data_loader.get_events.cache_clear()
    data_loader.get_lineups.cache_clear()


@pytest.fixture
def mock_competitions_df() -> pd.DataFrame:
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
def mock_matches_df() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "match_id": 12345,
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
def mock_events_df() -> pd.DataFrame:
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
def mock_lineups_dict() -> dict[str, pd.DataFrame]:
    # Mirrors the shape of sb.lineups(): one DataFrame per team, each player
    # carrying a "positions" list. Player D has no "Starting XI" entry, so
    # get_starting_xi() must leave them out.
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
