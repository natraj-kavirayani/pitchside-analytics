"""
Integration tests: MatchService wired to real sources and real analytics.

The unit tests check each analytics function alone. These check that the
layers agree with each other, e.g. that the summary strip, the xG
timeline and the shot map all count the same shots for a match, and that
caching works through the whole stack rather than only in isolation.
"""

import pytest

from pitchside.data.sample import COMPETITION_ID, MATCHES, SEASON_ID, SampleSource
from pitchside.data.source import CachedSource, StatsBombSource
from pitchside.service import DATA_SOURCE_ENV, MatchRef, MatchService, build_service
from tests.support import CountingSource

ALL_VIEWS_CALLS = ("teams", "shots", "shootout", "xg_timeline", "passers", "summary", "substitutions")


@pytest.fixture(scope="module")
def sample_service() -> MatchService:
    return MatchService(SampleSource())


# --- Browsing ----------------------------------------------------------------

@pytest.mark.integration
def test_matches_become_match_refs_with_labels(frames_service):
    refs = frames_service.matches(2, 44)
    assert [r.match_id for r in refs] == [12345, 67890]
    assert refs[0].label == "Home Team 2 - 1 Away Team (2016-05-01)"
    assert (refs[0].competition_id, refs[0].season_id) == (2, 44)


@pytest.mark.integration
def test_unknown_season_has_no_matches(frames_service):
    assert frames_service.matches(999, 1) == []


@pytest.mark.integration
def test_managers_are_looked_up_in_the_match_own_season(frames_service):
    match = frames_service.matches(11, 90)[1]
    assert frames_service.managers(match) == {"home": "Not available", "away": "Third Manager"}


@pytest.mark.integration
def test_match_ref_label_format():
    ref = MatchRef(1, 2, 3, "A", "B", 0, 4, "2020-01-01")
    assert ref.label == "A 0 - 4 B (2020-01-01)"


# --- Layers agree --------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("match", MATCHES, ids=lambda m: str(m.match_id))
def test_summary_timeline_and_shot_map_agree(sample_service, match):
    summary = sample_service.summary(match.match_id).set_index("team")
    timeline = sample_service.xg_timeline(match.match_id)
    shots = sample_service.shots(match.match_id)

    totals = timeline.groupby("team")["cumulative_xg"].last()
    for team in summary.index:
        assert summary.loc[team, "xg"] == pytest.approx(totals[team])
        assert summary.loc[team, "shots"] == (shots["team"] == team).sum()
        assert summary.loc[team, "shots"] == (timeline["team"] == team).sum() - 1, "Minus the kickoff row."


@pytest.mark.integration
@pytest.mark.parametrize("match", MATCHES, ids=lambda m: str(m.match_id))
def test_timeline_goals_match_the_scoreline(sample_service, match):
    timeline = sample_service.xg_timeline(match.match_id)
    goals = timeline[timeline["is_goal"].astype(bool)].groupby("team").size()
    assert goals.get(match.home_team, 0) == match.home_score
    assert goals.get(match.away_team, 0) == match.away_score


@pytest.mark.integration
def test_shootout_match_keeps_kicks_out_of_everything_but_the_shootout(sample_service):
    match = next(m for m in MATCHES if m.shootout)
    kicks = sample_service.shootout(match.match_id)
    assert len(kicks) == sum(len(team) for team in match.shootout)
    assert (sample_service.shots(match.match_id)["period"] < 5).all()


@pytest.mark.integration
@pytest.mark.parametrize("match", MATCHES, ids=lambda m: str(m.match_id))
def test_pass_network_uses_only_the_starting_xi(sample_service, match):
    xi = sample_service.starting_xi(match.match_id)
    for team in sample_service.teams(match.match_id):
        nodes, _ = sample_service.pass_network(match.match_id, team)
        assert set(nodes["player"]) <= set(xi[team]["player"])


@pytest.mark.integration
def test_sample_competition_is_browsable(sample_service):
    comps = sample_service.competitions()
    assert (comps["competition_id"] == COMPETITION_ID).any()
    assert len(sample_service.matches(COMPETITION_ID, SEASON_ID)) == len(MATCHES)


# --- Caching through the stack ----------------------------------------------

@pytest.mark.integration
def test_every_view_together_fetches_events_once(frames_source):
    counting = CountingSource(frames_source)
    service = MatchService(CachedSource(counting))
    for call in ALL_VIEWS_CALLS:
        getattr(service, call)(12345)
    for team in service.teams(12345):
        service.pass_network(12345, team)
    assert counting.calls.count(("events", 12345)) == 1


# --- build_service -------------------------------------------------------------

@pytest.mark.integration
def test_build_service_defaults_to_cached_statsbomb(monkeypatch):
    monkeypatch.delenv(DATA_SOURCE_ENV, raising=False)
    service = build_service()
    assert isinstance(service.source, CachedSource)
    assert isinstance(service.source.source, StatsBombSource)
    assert service.label == "StatsBomb open data"


@pytest.mark.integration
@pytest.mark.parametrize("value", ["sample", " Sample "])
def test_build_service_reads_the_environment(monkeypatch, value):
    monkeypatch.setenv(DATA_SOURCE_ENV, value)
    assert isinstance(build_service().source, SampleSource)


@pytest.mark.integration
def test_build_service_argument_beats_the_environment(monkeypatch):
    monkeypatch.setenv(DATA_SOURCE_ENV, "statsbomb")
    assert isinstance(build_service("sample").source, SampleSource)


@pytest.mark.integration
def test_build_service_rejects_unknown_sources():
    with pytest.raises(ValueError, match="'nope'"):
        build_service("nope")
