"""
Unit tests for the offline sample league (pitchside.data.sample).

The e2e smoke tests and the demo mode rely on the sample being stable and
internally consistent, so those are the properties checked here. Its
shape matching real StatsBomb data is checked in tests/contract.
"""

import pandas as pd
import pytest

from pitchside.data.sample import COMPETITION_ID, MATCHES, SEASON_ID, SampleSource


@pytest.fixture(scope="module")
def source() -> SampleSource:
    return SampleSource()


@pytest.mark.unit
def test_sample_is_deterministic(source):
    again = SampleSource()
    for match in MATCHES:
        pd.testing.assert_frame_equal(source.events(match.match_id), again.events(match.match_id))


@pytest.mark.unit
def test_sample_lists_every_match(source):
    matches = source.matches(COMPETITION_ID, SEASON_ID)
    assert list(matches["match_id"]) == [m.match_id for m in MATCHES]


@pytest.mark.unit
@pytest.mark.parametrize("match", MATCHES, ids=lambda m: str(m.match_id))
def test_sample_goals_match_the_scoreline(source, match):
    events = source.events(match.match_id)
    in_match = events[(events["type"] == "Shot") & (events["period"] < 5)]
    goals = in_match[in_match["shot_outcome"] == "Goal"].groupby("team").size()
    assert goals.get(match.home_team, 0) == match.home_score
    assert goals.get(match.away_team, 0) == match.away_score


@pytest.mark.unit
@pytest.mark.parametrize("match", MATCHES, ids=lambda m: str(m.match_id))
def test_sample_event_index_follows_match_time(source, match):
    events = source.events(match.match_id)
    assert events["index"].is_monotonic_increasing and events["index"].is_unique
    timing = list(zip(events["period"], events["minute"], events["second"]))
    assert timing == sorted(timing)


@pytest.mark.unit
@pytest.mark.parametrize("match", MATCHES, ids=lambda m: str(m.match_id))
def test_sample_substitutes_only_play_after_coming_on(source, match):
    events = source.events(match.match_id)
    subs = events[events["type"] == "Substitution"]
    for _, sub in subs.iterrows():
        team_events = events[events["team"] == sub["team"]]
        on_player = team_events[team_events["player"] == sub["substitution_replacement"]]
        off_player = team_events[(team_events["player"] == sub["player"]) & (team_events["type"] == "Pass")]
        assert (on_player["minute"] >= sub["minute"]).all()
        assert (off_player["minute"] < sub["minute"]).all()


@pytest.mark.unit
def test_sample_player_names_are_unique_across_the_league(source):
    teams_by_player: dict[str, set[str]] = {}
    for match in MATCHES:
        for team, squad in source.lineups(match.match_id).items():
            for name in squad["player_name"]:
                teams_by_player.setdefault(name, set()).add(team)
    assert all(len(teams) == 1 for teams in teams_by_player.values())


@pytest.mark.unit
def test_sample_lineups_have_eleven_starters_per_team(source):
    for match in MATCHES:
        for team, squad in source.lineups(match.match_id).items():
            starters = [p for p in squad["positions"] if p and p[0]["start_reason"] == "Starting XI"]
            assert len(starters) == 11, team


@pytest.mark.unit
def test_sample_covers_the_cases_the_app_treats_specially(source):
    """The sample exists to exercise these paths; losing one would quietly
    shrink what the e2e smoke tests cover."""
    has_shootout = [(source.events(m.match_id)["period"] == 5).any() for m in MATCHES]
    assert any(has_shootout) and not all(has_shootout)
    assert any(m.home_score == m.away_score == 0 for m in MATCHES)
    assert any(m.home_manager is None or m.away_manager is None for m in MATCHES)
