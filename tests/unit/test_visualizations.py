"""
Unit tests for visualizations.py chart-building functions.
"""

import pandas as pd
import pytest
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from visualizations import (
    _pitch,
    _vertical_pitch,
    plot_heatmap,
    plot_pass_map,
    plot_pass_network,
    plot_shot_map,
    plot_xg_timeline,
    shootout_table_html,
)


# --- pitch orientation ---------------------------------------------------------

@pytest.mark.unit
def test_pitch_is_horizontal():
    pitch = _pitch()
    assert pitch.vertical is False


@pytest.mark.unit
def test_vertical_pitch_is_vertical():
    pitch = _vertical_pitch()
    assert pitch.vertical is True


# --- plot_shot_map ---------------------------------------------------------------

@pytest.mark.unit
def test_plot_shot_map_returns_figure(mock_events_df: pd.DataFrame):
    shots = mock_events_df[mock_events_df["type"] == "Shot"].copy()
    fig = plot_shot_map(shots, title="Test Shot Map")
    assert isinstance(fig, Figure)
    plt.close(fig)


@pytest.mark.unit
def test_plot_shot_map_empty_dataframe():
    empty_shots = pd.DataFrame(columns=["location", "shot_outcome", "shot_statsbomb_xg"])
    fig = plot_shot_map(empty_shots, title="Empty Test")
    assert isinstance(fig, Figure)
    assert fig.axes[0].get_title() == "No shot data"
    plt.close(fig)


# --- plot_pass_map -----------------------------------------------------------------

@pytest.mark.unit
def test_plot_pass_map_returns_figure(mock_events_df: pd.DataFrame):
    passes = mock_events_df[mock_events_df["type"] == "Pass"].copy()
    fig = plot_pass_map(passes, title="Test Pass Map")
    assert isinstance(fig, Figure)
    plt.close(fig)


@pytest.mark.unit
def test_plot_pass_map_empty_dataframe():
    empty_passes = pd.DataFrame(columns=["location", "pass_end_location", "pass_outcome"])
    fig = plot_pass_map(empty_passes, title="Empty Test")
    assert isinstance(fig, Figure)
    assert fig.axes[0].get_title() == "No pass data"
    plt.close(fig)


# --- plot_heatmap ------------------------------------------------------------------

@pytest.mark.unit
def test_plot_heatmap_returns_figure(mock_events_df: pd.DataFrame):
    fig = plot_heatmap(mock_events_df, title="Test Heatmap")
    assert isinstance(fig, Figure)
    plt.close(fig)


@pytest.mark.unit
def test_plot_heatmap_no_location_data():
    events = pd.DataFrame([{"type": "Pass", "team": "Home Team", "location": None}])
    fig = plot_heatmap(events, title="Empty Test")
    assert isinstance(fig, Figure)
    assert fig.axes[0].get_title() == "No location data"
    plt.close(fig)


# --- plot_pass_network -------------------------------------------------------------

@pytest.mark.unit
def test_plot_pass_network_structure():
    nodes = pd.DataFrame([
        {"player": "Player A", "x": 40.0, "y": 30.0, "passes": 15},
        {"player": "Player B", "x": 60.0, "y": 40.0, "passes": 20},
    ])
    edges = pd.DataFrame([
        {
            "player": "Player A", "pass_recipient": "Player B", "count": 5,
            "x1": 40.0, "y1": 30.0, "x2": 60.0, "y2": 40.0,
        }
    ])
    fig = plot_pass_network(nodes, edges, title="Test Network")
    assert isinstance(fig, Figure)
    plt.close(fig)


@pytest.mark.unit
def test_plot_pass_network_uses_vertical_pitch():
    nodes = pd.DataFrame([{"player": "Player A", "x": 40.0, "y": 30.0, "passes": 1}])
    edges = pd.DataFrame(columns=["player", "pass_recipient", "count", "x1", "y1", "x2", "y2"])
    fig = plot_pass_network(nodes, edges, title="Test Network")
    # The pass network is documented (and expected by app.py's layout) to
    # use the vertical pitch orientation, not the default horizontal one.
    assert fig.get_figwidth() < fig.get_figheight()
    plt.close(fig)


@pytest.mark.unit
def test_plot_xg_timeline_draws_one_line_per_team_and_labels_totals():
    timeline = pd.DataFrame([
        {"team": "Away Team", "minute": 0.0, "xg": 0.0, "cumulative_xg": 0.0, "is_goal": False, "player": None},
        {"team": "Away Team", "minute": 40.0, "xg": 0.08, "cumulative_xg": 0.08, "is_goal": False, "player": "Player Y"},
        {"team": "Home Team", "minute": 0.0, "xg": 0.0, "cumulative_xg": 0.0, "is_goal": False, "player": None},
        {"team": "Home Team", "minute": 30.25, "xg": 0.35, "cumulative_xg": 0.35, "is_goal": True, "player": "Player B"},
    ])
    fig = plot_xg_timeline(timeline, title="Test xG")
    ax = fig.axes[0]
    assert isinstance(fig, Figure)
    assert len(ax.get_lines()) == 2, "Expected one step line per team."
    labels = {t.get_text() for t in ax.texts}
    assert labels == {"Away Team  0.08", "Home Team  0.35"}, "Each line needs a direct end label with its total xG."
    assert ax.get_legend() is not None
    plt.close(fig)


@pytest.mark.unit
def test_plot_xg_timeline_empty():
    empty = pd.DataFrame(columns=["team", "minute", "xg", "cumulative_xg", "is_goal", "player"])
    fig = plot_xg_timeline(empty, title="Empty Test")
    assert fig.axes[0].get_title() == "No shot data"
    plt.close(fig)


@pytest.mark.unit
def test_plot_pass_network_empty_nodes():
    empty = pd.DataFrame(columns=["player", "x", "y", "passes"])
    empty_edges = pd.DataFrame(columns=["player", "pass_recipient", "count", "x1", "y1", "x2", "y2"])
    fig = plot_pass_network(empty, empty_edges, title="Empty Test")
    assert isinstance(fig, Figure)
    assert fig.axes[0].get_title() == "No pass data"
    plt.close(fig)



@pytest.fixture
def early_finish_shootout() -> pd.DataFrame:
    """Away kicks first and scores 4 of 4; Home scores 1 of 3, so the
    shootout is decided before Home's 4th kick. One name has apostrophes."""
    return pd.DataFrame([
        {"team": "Away Team", "kick": 1, "player": "Player X", "scored": True},
        {"team": "Home Team", "kick": 1, "player": "Player A", "scored": True},
        {"team": "Away Team", "kick": 2, "player": "N'Golo O'Brien", "scored": True},
        {"team": "Home Team", "kick": 2, "player": "Player B", "scored": False},
        {"team": "Away Team", "kick": 3, "player": "Player Y", "scored": True},
        {"team": "Home Team", "kick": 3, "player": "Player C", "scored": False},
        {"team": "Away Team", "kick": 4, "player": "Player Z", "scored": True},
    ])


def _rows(html: str) -> list[str]:
    return html.split("<tbody>")[1].split("</tr>")[:-1]


@pytest.mark.unit
def test_shootout_table_empty_returns_empty_string():
    assert shootout_table_html(pd.DataFrame(columns=["team", "kick", "player", "scored"])) == ""


@pytest.mark.unit
def test_shootout_table_one_row_per_team_first_kicker_on_top(early_finish_shootout):
    rows = _rows(shootout_table_html(early_finish_shootout))
    assert len(rows) == 2
    assert "Away Team" in rows[0] and "Home Team" in rows[1]


@pytest.mark.unit
def test_shootout_table_marks_goals_and_misses_with_taker_tooltips(early_finish_shootout):
    away, home = _rows(shootout_table_html(early_finish_shootout))
    assert away.count("✅") == 4 and "🔴" not in away
    assert home.count("✅") == 1 and home.count("🔴") == 2
    assert 'title="Player B"' in home
    assert 'aria-label="Player B missed"' in home


@pytest.mark.unit
def test_shootout_table_leaves_untaken_kicks_blank_and_shows_totals(early_finish_shootout):
    html = shootout_table_html(early_finish_shootout)
    assert html.count("<th ") == 6, "Blank corner + kicks 1-4 + Total."
    away, home = _rows(html)
    assert away.count("<td") == home.count("<td") == 6
    assert home.count("title=") == 3, "Home's 4th kick was never taken."
    assert away.endswith(">4</td>") and home.endswith(">1</td>")


@pytest.mark.unit
def test_shootout_table_escapes_player_names(early_finish_shootout):
    html = shootout_table_html(early_finish_shootout)
    assert 'title="N&#x27;Golo O&#x27;Brien"' in html
