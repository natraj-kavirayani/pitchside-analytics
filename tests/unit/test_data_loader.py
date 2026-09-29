"""
Unit tests for data_loader.py.

Every StatsBomb API call (sb.competitions, sb.matches, sb.events,
sb.lineups) is mocked at the point data_loader calls it - none of these
tests touch the network or StatsBomb's open-data GitHub repository.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from data_loader import (
    get_competitions,
    get_events,
    get_lineups,
    get_managers,
    get_matches,
    get_pass_network,
    get_passes,
    get_shootout,
    get_shots,
    get_starting_xi,
    get_substitutions,
    get_xg_timeline,
    teams_in_match,
)


# --- get_competitions -------------------------------------------------------

@pytest.mark.unit
def test_get_competitions_returns_mocked_data(mock_competitions_df):
    with patch("data_loader.sb.competitions", return_value=mock_competitions_df) as mock_call:
        result = get_competitions()
        pd.testing.assert_frame_equal(result, mock_competitions_df)
        mock_call.assert_called_once_with()


@pytest.mark.unit
def test_get_competitions_is_cached(mock_competitions_df):
    with patch("data_loader.sb.competitions", return_value=mock_competitions_df) as mock_call:
        get_competitions()
        get_competitions()
        assert mock_call.call_count == 1, "get_competitions() should only hit the API once."


# --- get_matches -------------------------------------------------------------

@pytest.mark.unit
def test_get_matches_calls_sb_with_correct_ids(mock_matches_df):
    with patch("data_loader.sb.matches", return_value=mock_matches_df) as mock_call:
        result = get_matches(competition_id=2, season_id=44)
        pd.testing.assert_frame_equal(result, mock_matches_df)
        mock_call.assert_called_once_with(competition_id=2, season_id=44)


@pytest.mark.unit
def test_get_matches_is_cached_per_id_pair(mock_matches_df):
    with patch("data_loader.sb.matches", return_value=mock_matches_df) as mock_call:
        get_matches(competition_id=2, season_id=44)
        get_matches(competition_id=2, season_id=44)
        assert mock_call.call_count == 1
        get_matches(competition_id=11, season_id=90)
        assert mock_call.call_count == 2, "A different id pair must not reuse the cached result."


# --- get_events ----------------------------------------------------------------

@pytest.mark.unit
def test_get_events_calls_sb_with_match_id(mock_events_df):
    with patch("data_loader.sb.events", return_value=mock_events_df) as mock_call:
        result = get_events(match_id=12345)
        pd.testing.assert_frame_equal(result, mock_events_df)
        mock_call.assert_called_once_with(match_id=12345)


# --- get_shots -----------------------------------------------------------------

@pytest.mark.unit
def test_get_shots_filters_to_shot_type_only(mock_events_df):
    with patch("data_loader.get_events", return_value=mock_events_df):
        shots = get_shots(match_id=12345)
        assert set(shots["type"]) == {"Shot"}
        assert len(shots) == 2


@pytest.mark.unit
def test_get_shots_filters_by_team(mock_events_df):
    with patch("data_loader.get_events", return_value=mock_events_df):
        shots = get_shots(match_id=12345, team="Away Team")
        assert len(shots) == 1
        assert shots.iloc[0]["player"] == "Player Y"


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


@pytest.mark.unit
def test_get_shots_excludes_penalty_shootout(shootout_events):
    with patch("data_loader.get_events", return_value=shootout_events):
        shots = get_shots(match_id=12345)
        assert list(shots["player"]) == ["Player A", "Player X"]


# --- get_passes ------------------------------------------------------------------

@pytest.mark.unit
def test_get_passes_filters_to_pass_type_only(mock_events_df):
    with patch("data_loader.get_events", return_value=mock_events_df):
        passes = get_passes(match_id=12345)
        assert set(passes["type"]) == {"Pass"}


@pytest.mark.unit
def test_get_passes_filters_by_team_and_player(mock_events_df):
    with patch("data_loader.get_events", return_value=mock_events_df):
        passes = get_passes(match_id=12345, team="Home Team", player="Player A")
        assert len(passes) == 1
        assert passes.iloc[0]["player"] == "Player A"


@pytest.mark.unit
def test_get_passes_drops_rows_missing_location():
    events = pd.DataFrame([
        {
            "type": "Pass", "team": "Home Team", "player": "Player A",
            "location": [10.0, 20.0], "pass_end_location": None,
            "pass_outcome": float("nan"), "pass_recipient": "Player B",
            "minute": 5, "second": 0,
        },
        {
            "type": "Pass", "team": "Home Team", "player": "Player B",
            "location": [30.0, 40.0], "pass_end_location": [50.0, 50.0],
            "pass_outcome": float("nan"), "pass_recipient": "Player A",
            "minute": 6, "second": 0,
        },
    ])
    with patch("data_loader.get_events", return_value=events):
        passes = get_passes(match_id=12345)
        assert len(passes) == 1
        assert passes.iloc[0]["player"] == "Player B"


# --- teams_in_match --------------------------------------------------------------

@pytest.mark.unit
def test_teams_in_match_returns_sorted_unique_teams(mock_events_df):
    with patch("data_loader.get_events", return_value=mock_events_df):
        teams = teams_in_match(match_id=12345)
        assert teams == ["Away Team", "Home Team"]


# --- get_lineups -----------------------------------------------------------------

@pytest.mark.unit
def test_get_lineups_calls_sb_with_match_id(mock_lineups_dict):
    with patch("data_loader.sb.lineups", return_value=mock_lineups_dict) as mock_call:
        result = get_lineups(match_id=12345)
        assert result == mock_lineups_dict
        mock_call.assert_called_once_with(match_id=12345)


# --- get_starting_xi ---------------------------------------------------------------

@pytest.mark.unit
def test_get_starting_xi_excludes_non_starters(mock_lineups_dict):
    with patch("data_loader.get_lineups", return_value=mock_lineups_dict):
        starting_xi = get_starting_xi(match_id=12345)

        home = starting_xi["Home Team"]
        assert len(home) == 2, "Player D has no Starting XI entry and must be excluded."
        assert "Player D" not in home["player"].values
        assert list(home["jersey_number"]) == [9, 10]

        away = starting_xi["Away Team"]
        assert len(away) == 1
        assert away.iloc[0]["player"] == "Player X"


@pytest.mark.unit
def test_get_starting_xi_handles_team_with_no_starters():
    lineups = {
        "Home Team": pd.DataFrame([
            {"player_name": "Sub Only", "jersey_number": 22, "positions": []},
        ]),
    }
    with patch("data_loader.get_lineups", return_value=lineups):
        starting_xi = get_starting_xi(match_id=12345)
        assert starting_xi["Home Team"].empty
        assert list(starting_xi["Home Team"].columns) == ["player", "jersey_number", "position"]


# --- get_substitutions -----------------------------------------------------------------

@pytest.mark.unit
def test_get_substitutions_empty():
    empty_events = pd.DataFrame(columns=["type", "team", "minute", "second", "player"])
    with patch("data_loader.get_events", return_value=empty_events):
        subs = get_substitutions(match_id=12345)
        assert isinstance(subs, pd.DataFrame)
        assert subs.empty
        assert list(subs.columns) == ["team", "minute", "second", "player_off", "player_on"]


@pytest.mark.unit
def test_get_substitutions_sorted_by_time_both_teams():
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
    with patch("data_loader.get_events", return_value=events):
        subs = get_substitutions(match_id=12345)
        assert len(subs) == 2
        # Sorted by minute ascending, so the 60' sub comes before the 70' one.
        assert subs.iloc[0]["team"] == "Home Team"
        assert subs.iloc[0]["player_off"] == "Player A"
        assert subs.iloc[0]["player_on"] == "Player C"
        assert subs.iloc[1]["team"] == "Away Team"


@pytest.mark.unit
def test_get_substitutions_defaults_missing_columns():
    # No "second" or "substitution_replacement" column at all.
    events = pd.DataFrame([
        {"type": "Substitution", "team": "Home Team", "player": "Player A", "minute": 60},
    ])
    with patch("data_loader.get_events", return_value=events):
        subs = get_substitutions(match_id=12345)
        assert subs.iloc[0]["second"] == 0
        assert subs.iloc[0]["player_on"] == "Unknown"


# --- get_managers -----------------------------------------------------------------

@pytest.mark.unit
def test_get_managers_found(mock_matches_df):
    with patch("data_loader.get_matches", return_value=mock_matches_df):
        managers = get_managers(competition_id=2, season_id=44, match_id=12345)
        assert managers == {"home": "Home Manager", "away": "Away Manager"}


@pytest.mark.unit
def test_get_managers_defaults_missing_manager_to_not_available(mock_matches_df):
    with patch("data_loader.get_matches", return_value=mock_matches_df):
        # match_id 67890 has home_managers=None in the fixture.
        managers = get_managers(competition_id=2, season_id=44, match_id=67890)
        assert managers == {"home": "Not available", "away": "Third Manager"}


@pytest.mark.unit
def test_get_managers_match_not_found(mock_matches_df):
    with patch("data_loader.get_matches", return_value=mock_matches_df):
        managers = get_managers(competition_id=2, season_id=44, match_id=99999)
        assert managers == {"home": "Not available", "away": "Not available"}


# --- get_pass_network -----------------------------------------------------------------

@pytest.mark.unit
def test_get_pass_network_until_first_sub(mock_events_df):
    with patch("data_loader.get_events", return_value=mock_events_df):
        nodes, edges = get_pass_network(match_id=12345, team="Home Team", until_first_sub=True)

        # Passes at minute 15 and 25 are included; minute 70 pass (after the
        # minute-60 substitution) must be filtered out.
        assert not nodes.empty
        assert set(nodes["player"]) == {"Player A", "Player B"}
        assert "Player C" not in nodes["player"].values

        assert len(edges) == 1
        assert edges.iloc[0]["player"] == "Player A"
        assert edges.iloc[0]["pass_recipient"] == "Player B"
        assert edges.iloc[0]["count"] == 1


@pytest.mark.unit
def test_get_pass_network_without_until_first_sub_includes_post_sub_passes(mock_events_df):
    with patch("data_loader.get_events", return_value=mock_events_df):
        nodes, _ = get_pass_network(match_id=12345, team="Home Team", until_first_sub=False)
        assert "Player C" in nodes["player"].values


@pytest.mark.unit
def test_get_pass_network_no_passes_returns_empty_frames_with_expected_columns():
    events = pd.DataFrame(columns=["type", "team", "location", "player", "minute", "pass_recipient"])
    with patch("data_loader.get_events", return_value=events):
        nodes, edges = get_pass_network(match_id=12345, team="Home Team")
        assert nodes.empty
        assert list(nodes.columns) == ["player", "x", "y", "passes"]
        assert edges.empty
        assert list(edges.columns) == ["player", "pass_recipient", "count", "x1", "y1", "x2", "y2"]


# --- get_xg_timeline -----------------------------------------------------------------

@pytest.mark.unit
def test_get_xg_timeline_accumulates_xg_per_team(mock_events_df):
    with patch("data_loader.get_events", return_value=mock_events_df):
        timeline = get_xg_timeline(match_id=12345)

        home = timeline[timeline["team"] == "Home Team"]
        assert list(home["minute"]) == [0.0, 30.25], "Kickoff row, then the 30:15 shot."
        assert list(home["cumulative_xg"]) == pytest.approx([0.0, 0.35])
        assert list(home["is_goal"]) == [False, True]

        away = timeline[timeline["team"] == "Away Team"]
        assert away["cumulative_xg"].iloc[-1] == pytest.approx(0.08)
        assert not away["is_goal"].any()


@pytest.mark.unit
def test_get_xg_timeline_team_without_shots_gets_flat_line():
    events = pd.DataFrame([
        {"type": "Pass", "team": "Home Team", "player": "Player A", "minute": 5, "second": 0},
        {
            "type": "Shot", "team": "Away Team", "player": "Player Y", "minute": 10, "second": 0,
            "shot_outcome": "Saved", "shot_statsbomb_xg": 0.2,
        },
    ])
    with patch("data_loader.get_events", return_value=events):
        timeline = get_xg_timeline(match_id=12345)
        home = timeline[timeline["team"] == "Home Team"]
        assert len(home) == 1
        assert home.iloc[0]["cumulative_xg"] == 0.0


@pytest.mark.unit
def test_get_xg_timeline_orders_shots_within_the_same_minute_by_second():
    events = pd.DataFrame([
        {"type": "Shot", "team": "Home Team", "player": "Late", "minute": 20, "second": 50,
         "shot_outcome": "Goal", "shot_statsbomb_xg": 0.5},
        {"type": "Shot", "team": "Home Team", "player": "Early", "minute": 20, "second": 5,
         "shot_outcome": "Saved", "shot_statsbomb_xg": 0.1},
    ])
    with patch("data_loader.get_events", return_value=events):
        timeline = get_xg_timeline(match_id=12345)
        assert list(timeline["player"].dropna()) == ["Early", "Late"]
        assert list(timeline["cumulative_xg"]) == pytest.approx([0.0, 0.1, 0.6])


@pytest.mark.unit
def test_get_xg_timeline_no_events_returns_empty_frame_with_expected_columns():
    events = pd.DataFrame(columns=["type", "team", "minute", "second", "player"])
    with patch("data_loader.get_events", return_value=events):
        timeline = get_xg_timeline(match_id=12345)
        assert timeline.empty
        assert list(timeline.columns) == ["team", "minute", "xg", "cumulative_xg", "is_goal", "player"]


@pytest.mark.unit
def test_get_xg_timeline_excludes_penalty_shootout(shootout_events):
    """Shootout kicks aren't chances within the match: including them used
    to push a 1-1 draw to 8+ cumulative xG per team."""
    with patch("data_loader.get_events", return_value=shootout_events):
        timeline = get_xg_timeline(match_id=12345)
        totals = timeline.groupby("team")["cumulative_xg"].last()
        assert totals["Home Team"] == pytest.approx(0.30)
        assert totals["Away Team"] == pytest.approx(0.10)
        assert timeline["minute"].max() == 110


# --- get_shootout -----------------------------------------------------------------

@pytest.mark.unit
def test_get_shootout_numbers_kicks_per_team_in_order_taken(shootout_events):
    # Add a third kick, listed out of order, to check sorting by event index.
    extra = pd.DataFrame([{
        "type": "Shot", "team": "Home Team", "player": "Player C", "period": 5,
        "minute": 122, "second": 0, "shot_statsbomb_xg": 0.78, "shot_outcome": "Post",
    }])
    events = pd.concat([extra, shootout_events], ignore_index=True)
    events["index"] = [5, 1, 2, 3, 4]
    with patch("data_loader.get_events", return_value=events):
        shootout = get_shootout(match_id=12345)
        assert list(shootout["player"]) == ["Player B", "Player Y", "Player C"]
        assert list(shootout["team"]) == ["Home Team", "Away Team", "Home Team"]
        assert list(shootout["kick"]) == [1, 1, 2]
        assert list(shootout["scored"]) == [True, False, False]


@pytest.mark.unit
def test_get_shootout_empty_when_match_had_none(mock_events_df):
    with patch("data_loader.get_events", return_value=mock_events_df):
        shootout = get_shootout(match_id=12345)
        assert shootout.empty
        assert list(shootout.columns) == ["team", "kick", "player", "scored"]


@pytest.mark.unit
def test_get_shootout_empty_when_no_period_5_shots(shootout_events):
    regulation_only = shootout_events[shootout_events["period"] != 5]
    with patch("data_loader.get_events", return_value=regulation_only):
        assert get_shootout(match_id=12345).empty
