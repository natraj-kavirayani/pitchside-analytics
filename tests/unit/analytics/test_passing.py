"""Unit tests for pitchside.analytics.passing: passes and pass networks."""

import pandas as pd
import pytest

from pitchside.analytics.passing import EDGE_COLUMNS, NODE_COLUMNS, pass_network, passers, passes


# --- passes ------------------------------------------------------------------

@pytest.mark.unit
def test_passes_filters_to_pass_type_only(events_frame):
    assert set(passes(events_frame)["type"]) == {"Pass"}


@pytest.mark.unit
def test_passes_filters_by_team_and_player(events_frame):
    result = passes(events_frame, team="Home Team", player="Player A")
    assert len(result) == 1
    assert result.iloc[0]["player"] == "Player A"


@pytest.mark.unit
def test_passes_drops_rows_missing_location():
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
    result = passes(events)
    assert len(result) == 1
    assert result.iloc[0]["player"] == "Player B"


# --- passers -----------------------------------------------------------------

@pytest.mark.unit
def test_passers_lists_each_passer_once_sorted(events_frame):
    # Player A passes, then is substituted; Player C replaces them and passes.
    assert passers(events_frame) == ["Player A", "Player B", "Player C", "Player X"]


# --- pass_network ------------------------------------------------------------

@pytest.mark.unit
def test_pass_network_until_first_sub(events_frame):
    nodes, edges = pass_network(events_frame, team="Home Team", until_first_sub=True)

    # Passes at minute 15 and 25 are included; minute 70 pass (after the
    # minute-60 substitution) must be filtered out.
    assert set(nodes["player"]) == {"Player A", "Player B"}

    assert len(edges) == 1
    assert edges.iloc[0]["player"] == "Player A"
    assert edges.iloc[0]["pass_recipient"] == "Player B"
    assert edges.iloc[0]["count"] == 1


@pytest.mark.unit
def test_pass_network_without_until_first_sub_includes_post_sub_passes(events_frame):
    nodes, _ = pass_network(events_frame, team="Home Team", until_first_sub=False)
    assert "Player C" in nodes["player"].values


@pytest.mark.unit
def test_pass_network_node_sits_at_average_pass_location():
    events = pd.DataFrame([
        {"type": "Pass", "team": "T", "player": "P", "location": [10.0, 20.0],
         "pass_outcome": float("nan"), "pass_recipient": None, "minute": 1},
        {"type": "Pass", "team": "T", "player": "P", "location": [30.0, 40.0],
         "pass_outcome": float("nan"), "pass_recipient": None, "minute": 2},
    ])
    nodes, edges = pass_network(events, team="T")
    assert nodes.iloc[0][["x", "y", "passes"]].tolist() == [20.0, 30.0, 2]
    assert edges.empty, "Passes without a recipient can't form an edge."


@pytest.mark.unit
def test_pass_network_edge_to_player_without_own_passes_is_dropped():
    # Player B receives but never passes, so has no average position to draw to.
    events = pd.DataFrame([
        {"type": "Pass", "team": "T", "player": "A", "location": [10.0, 20.0],
         "pass_outcome": float("nan"), "pass_recipient": "B", "minute": 1},
    ])
    _, edges = pass_network(events, team="T")
    assert edges.empty
    assert list(edges.columns) == EDGE_COLUMNS


@pytest.mark.unit
def test_pass_network_no_passes_returns_empty_frames_with_expected_columns():
    events = pd.DataFrame(columns=["type", "team", "location", "player", "minute", "pass_recipient"])
    nodes, edges = pass_network(events, team="Home Team")
    assert nodes.empty and list(nodes.columns) == NODE_COLUMNS
    assert edges.empty and list(edges.columns) == EDGE_COLUMNS
