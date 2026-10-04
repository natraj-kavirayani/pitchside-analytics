"""
Property-based tests for the analytics layer (Hypothesis).

The example-based tests pin down known cases. These generate hundreds of
random matches (any mix of passes, shots and shootout kicks) and check
rules that must hold for every one of them, such as "cumulative xG never
goes down" or "a function never modifies the frame it was given". When a
rule breaks, Hypothesis shrinks the failing match to the smallest
example it can find.
"""

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pitchside.analytics.passing import pass_network, passes
from pitchside.analytics.shots import SHOOTOUT_PERIOD, match_shots, shootout, xg_timeline
from pitchside.analytics.summary import team_summary
from pitchside.viz.tables import split_share

TEAMS = ["Alpha", "Beta"]
PLAYERS = ["P1", "P2", "P3", "P4"]

coordinate = st.tuples(st.floats(0, 120), st.floats(0, 80)).map(list)
timing = st.fixed_dictionaries({
    "period": st.integers(1, 4),
    "minute": st.integers(0, 120),
    "second": st.integers(0, 59),
})


def _with(base: st.SearchStrategy, **fields) -> st.SearchStrategy:
    return st.tuples(base, st.fixed_dictionaries(fields)).map(lambda t: {**t[0], **t[1]})


shot_event = _with(
    timing, type=st.just("Shot"), team=st.sampled_from(TEAMS), player=st.sampled_from(PLAYERS),
    location=coordinate, shot_statsbomb_xg=st.floats(0, 1),
    shot_outcome=st.sampled_from(["Goal", "Saved", "Off T", "Blocked", "Post"]),
)
shootout_kick = shot_event.map(lambda e: {**e, "period": SHOOTOUT_PERIOD})
pass_event = _with(
    timing, type=st.just("Pass"), team=st.sampled_from(TEAMS), player=st.sampled_from(PLAYERS),
    location=coordinate, pass_end_location=coordinate,
    pass_recipient=st.sampled_from(PLAYERS), pass_outcome=st.sampled_from([None, "Incomplete", "Out"]),
)
substitution = _with(
    timing, type=st.just("Substitution"), team=st.sampled_from(TEAMS), player=st.sampled_from(PLAYERS),
    substitution_replacement=st.just("Sub"),
)
COLUMNS = ["period", "minute", "second", "type", "team", "player", "location",
           "shot_statsbomb_xg", "shot_outcome", "pass_end_location", "pass_recipient",
           "pass_outcome", "substitution_replacement"]

matches = st.lists(
    st.one_of(shot_event, shootout_kick, pass_event, substitution), max_size=40,
).map(lambda rows: pd.DataFrame(rows, columns=COLUMNS))


@pytest.mark.unit
@given(matches)
def test_cumulative_xg_never_decreases_and_totals_match_shots(events):
    timeline = xg_timeline(events)
    shots = match_shots(events)
    for team, rows in timeline.groupby("team"):
        assert rows["minute"].is_monotonic_increasing
        assert rows["cumulative_xg"].is_monotonic_increasing
        assert rows.iloc[0][["minute", "cumulative_xg"]].tolist() == [0.0, 0.0], "Every line starts at kickoff."
        expected = shots.loc[shots["team"] == team, "shot_statsbomb_xg"].sum()
        assert rows["cumulative_xg"].iloc[-1] == pytest.approx(expected)


@pytest.mark.unit
@given(matches)
def test_shootout_kicks_are_never_match_shots(events):
    assert (match_shots(events)["period"] != SHOOTOUT_PERIOD).all()
    kicks = shootout(events)
    assert len(kicks) == (events["period"] == SHOOTOUT_PERIOD).sum()
    for _, team_kicks in kicks.groupby("team"):
        assert list(team_kicks["kick"]) == list(range(1, len(team_kicks) + 1))


@pytest.mark.unit
@given(matches)
def test_summary_counts_are_consistent(events):
    summary = team_summary(events)
    assert (summary["on_target"] <= summary["shots"]).all()
    assert summary["pass_completion"].between(0, 100).all()
    assert summary["shots"].sum() == len(match_shots(events))
    assert summary["passes"].sum() == (events["type"] == "Pass").sum()


@pytest.mark.unit
@given(matches, st.sampled_from(TEAMS), st.booleans())
def test_pass_network_counts_every_pass_once(events, team, until_first_sub):
    nodes, edges = pass_network(events, team, until_first_sub=until_first_sub)
    team_passes = passes(events, team=team)
    assert nodes["passes"].sum() <= len(team_passes)
    if not until_first_sub:
        assert nodes["passes"].sum() == len(team_passes)
    completed = team_passes["pass_outcome"].isna().sum()
    assert edges["count"].sum() <= completed
    assert set(edges["player"]) <= set(nodes["player"])
    assert set(edges["pass_recipient"]) <= set(nodes["player"])


@pytest.mark.unit
@settings(max_examples=50)
@given(matches)
def test_analytics_never_modify_their_input(events):
    """Sources hand the same cached frame to every caller, so one function
    changing it would corrupt what the next one sees."""
    before = events.copy(deep=True)
    xg_timeline(events)
    shootout(events)
    team_summary(events)
    for team in TEAMS:
        pass_network(events, team)
    pd.testing.assert_frame_equal(events, before)


@pytest.mark.unit
@given(st.floats(0, 1e6), st.floats(0, 1e6))
def test_split_share_is_a_percentage_that_mirrors(left, right):
    share = split_share(left, right)
    assert 0 <= share <= 100
    assert share + split_share(right, left) == pytest.approx(100)
