"""Unit tests for pitchside.viz.tables: shootout table and summary strip."""

import re

import pandas as pd
import pytest

from pitchside.viz.palette import TEAM_COLORS
from pitchside.viz.tables import SUMMARY_STATS, shootout_table_html, split_share, summary_html


# --- shootout_table_html -----------------------------------------------------

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


# --- split_share -------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize(("left", "right", "expected"), [
    (1, 1, 50.0), (3, 1, 75.0), (0, 5, 0.0), (0, 0, 50.0),
])
def test_split_share(left, right, expected):
    assert split_share(left, right) == pytest.approx(expected)


# --- summary_html ------------------------------------------------------------

@pytest.fixture
def summary() -> pd.DataFrame:
    return pd.DataFrame([
        {"team": "Alpha <FC>", "xg": 1.234, "shots": 9, "on_target": 3, "passes": 400, "pass_completion": 81.4},
        {"team": "Beta", "xg": 0.0, "shots": 0, "on_target": 0, "passes": 100, "pass_completion": 70.0},
    ])


@pytest.mark.unit
@pytest.mark.parametrize("teams", [0, 1, 3])
def test_summary_html_needs_exactly_two_teams(summary, teams):
    frame = pd.concat([summary] * 2).head(teams)
    assert summary_html(frame) == ""


@pytest.mark.unit
def test_summary_html_one_row_per_stat_with_formatted_values(summary):
    html = summary_html(summary)
    assert html.count('class="ps-stat"') == len(SUMMARY_STATS)
    for value in ("<b>1.23</b>", "<b>0.00</b>", "<b>9</b>", "<b>81%</b>", "<b>70%</b>"):
        assert value in html


@pytest.mark.unit
def test_summary_html_numbers_rows_for_the_stagger_animation(summary):
    indexes = re.findall(r'class="ps-stat" style="--i:(\d+);', summary_html(summary))
    assert indexes == [str(i) for i in range(len(SUMMARY_STATS))]


@pytest.mark.unit
def test_summary_html_bars_split_in_proportion(summary):
    widths = re.findall(r"calc\(([\d.]+)% - 1\.5px\)", summary_html(summary))
    # xG 1.234 vs 0 -> 100%; shots 9 vs 0 -> 100%; on target 3 vs 0 -> 100%;
    # passes 400 vs 100 -> 80%; completion 81.4 vs 70 -> 53.8%.
    assert widths == ["100.0", "100.0", "100.0", "80.0", "53.8"]


@pytest.mark.unit
def test_summary_html_uses_team_colours_and_escapes_names(summary):
    html = summary_html(summary)
    assert "Alpha &lt;FC&gt;" in html and "<FC>" not in html
    assert TEAM_COLORS[0] in html and TEAM_COLORS[1] in html


@pytest.mark.unit
def test_summary_html_is_a_single_line(summary):
    # A newline followed by indentation would turn the rest into a Markdown code block.
    assert "\n" not in summary_html(summary)
