"""
Contract tests: does each data source supply what the app relies on?

Every other layer trusts that frames have certain columns and certain
kinds of values (e.g. "a completed pass has no outcome", "shootout kicks
are period 5"). These tests check those assumptions against each source:

- ``sample``: the offline sample league. Runs in every test run, so the
  sample can't drift away from the shape of the real data.
- ``statsbomb``: the live open data (marked ``live``, opt-in with
  ``pytest -m live``). Catches an upstream rename or format change with a
  precise failure, instead of a chart quietly going blank.

Both use a match with a penalty shootout, so the shootout assumptions are
checked too: the 2022 World Cup final for live data.
"""

import numbers

import pandas as pd
import pytest

from pitchside.data import sample
from pitchside.data.schema import (
    COMPETITION_COLUMNS,
    LINEUP_COLUMNS,
    MATCH_COLUMNS,
    event_contract,
    missing_columns,
)
from pitchside.data.source import CachedSource, MatchDataSource, StatsBombSource

# StatsBomb's ids for the 2022 FIFA World Cup and its final.
WORLD_CUP_2022 = (43, 106)
WORLD_CUP_2022_FINAL = 3869685

# Outcomes the analytics recognise. A completed pass has NO outcome
# (NaN); if StatsBomb ever started writing "Complete", every pass would
# count as incomplete and the pass map and network would go wrong.
KNOWN_PASS_OUTCOMES = {"Incomplete", "Out", "Unknown", "Pass Offside", "Injury Clearance"}
KNOWN_SHOT_OUTCOMES = {"Goal", "Saved", "Saved To Post", "Saved Off Target", "Off T",
                       "Blocked", "Wayward", "Post"}


class Case:
    def __init__(self, source: MatchDataSource, competition: tuple[int, int], match_id: int) -> None:
        self.source = source
        self.competition = competition
        self.match_id = match_id


@pytest.fixture(scope="module", params=[
    pytest.param("sample", marks=pytest.mark.contract),
    pytest.param("statsbomb", marks=[pytest.mark.contract, pytest.mark.live]),
])
def case(request) -> Case:
    if request.param == "sample":
        shootout_match = next(m for m in sample.MATCHES if m.shootout)
        return Case(sample.SampleSource(), (sample.COMPETITION_ID, sample.SEASON_ID),
                    shootout_match.match_id)
    return Case(CachedSource(StatsBombSource()), WORLD_CUP_2022, WORLD_CUP_2022_FINAL)


@pytest.fixture(scope="module")
def events(case) -> pd.DataFrame:
    return case.source.events(case.match_id)


def _is_point(value) -> bool:
    return (isinstance(value, (list, tuple)) and len(value) >= 2
            and all(isinstance(v, numbers.Real) for v in value[:2]))


def test_competitions_have_required_columns(case):
    comps = case.source.competitions()
    assert not missing_columns(comps, COMPETITION_COLUMNS)
    ids = set(zip(comps["competition_id"], comps["season_id"]))
    assert case.competition in ids


def test_matches_have_required_columns_and_integer_scores(case):
    matches = case.source.matches(*case.competition)
    assert not missing_columns(matches, MATCH_COLUMNS)
    assert case.match_id in set(matches["match_id"])
    assert pd.api.types.is_integer_dtype(matches["home_score"])
    assert pd.api.types.is_integer_dtype(matches["away_score"])


def test_events_have_required_columns(events):
    assert not missing_columns(events, event_contract(events))


def test_event_locations_are_xy_points(events):
    located = events["location"].dropna()
    assert len(located) and located.map(_is_point).all()
    passes = events[events["type"] == "Pass"]
    assert passes["pass_end_location"].dropna().map(_is_point).all()


def test_completed_passes_have_no_outcome(events):
    outcomes = set(events.loc[events["type"] == "Pass", "pass_outcome"].dropna())
    assert outcomes <= KNOWN_PASS_OUTCOMES, f"Unexpected pass outcomes: {outcomes - KNOWN_PASS_OUTCOMES}"
    assert events.loc[events["type"] == "Pass", "pass_outcome"].isna().any()


def test_shots_have_known_outcomes_and_xg_between_0_and_1(events):
    shots = events[events["type"] == "Shot"]
    assert set(shots["shot_outcome"]) <= KNOWN_SHOT_OUTCOMES
    assert shots["shot_statsbomb_xg"].between(0, 1).all()


def test_shootout_kicks_are_period_5(events):
    assert set(events["period"].dropna()) >= {1, 2, 5}
    assert (events.loc[events["period"] == 5, "type"] == "Shot").any()


def test_event_index_is_a_unique_sequence(events):
    assert events["index"].is_unique


def test_lineups_have_required_columns_and_starting_xi(case):
    lineups = case.source.lineups(case.match_id)
    assert len(lineups) == 2
    for team, squad in lineups.items():
        assert not missing_columns(squad, LINEUP_COLUMNS), team
        reasons = [p.get("start_reason") for positions in squad["positions"] for p in positions]
        assert reasons.count("Starting XI") == 11, team
        assert all("position" in p for positions in squad["positions"] for p in positions)
