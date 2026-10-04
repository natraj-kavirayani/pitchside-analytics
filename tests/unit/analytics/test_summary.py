"""Unit tests for pitchside.analytics.summary.team_summary."""

import pandas as pd
import pytest

from pitchside.analytics.summary import SUMMARY_COLUMNS, team_summary


@pytest.mark.unit
def test_summary_has_one_row_per_team_sorted(events_frame):
    summary = team_summary(events_frame)
    assert list(summary.columns) == SUMMARY_COLUMNS
    assert list(summary["team"]) == ["Away Team", "Home Team"]


@pytest.mark.unit
def test_summary_counts_shots_xg_and_passes(events_frame):
    home = team_summary(events_frame).set_index("team").loc["Home Team"]
    assert home["shots"] == 1
    assert home["on_target"] == 1, "A goal is on target."
    assert home["xg"] == pytest.approx(0.35)
    assert home["passes"] == 3
    assert home["pass_completion"] == pytest.approx(200 / 3), "2 of 3 passes had no outcome (completed)."


@pytest.mark.unit
def test_summary_off_target_shot_is_not_on_target(events_frame):
    away = team_summary(events_frame).set_index("team").loc["Away Team"]
    assert away["shots"] == 1 and away["on_target"] == 0


@pytest.mark.unit
def test_summary_leaves_out_shootout_kicks(shootout_events):
    summary = team_summary(shootout_events).set_index("team")
    assert summary.loc["Home Team", "shots"] == 1
    assert summary.loc["Home Team", "xg"] == pytest.approx(0.30)


@pytest.mark.unit
def test_summary_team_with_no_passes_or_shots_gets_zeros():
    events = pd.DataFrame([
        {"type": "Pass", "team": "A", "player": "P", "pass_outcome": float("nan")},
        {"type": "Pressure", "team": "B", "player": "Q"},
    ])
    b = team_summary(events).set_index("team").loc["B"]
    assert b[["xg", "shots", "on_target", "passes", "pass_completion"]].tolist() == [0, 0, 0, 0, 0]


@pytest.mark.unit
def test_summary_empty_events_gives_empty_frame():
    summary = team_summary(pd.DataFrame(columns=["type", "team"]))
    assert summary.empty and list(summary.columns) == SUMMARY_COLUMNS
