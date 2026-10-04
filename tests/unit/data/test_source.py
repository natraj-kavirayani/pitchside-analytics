"""
Unit tests for pitchside.data.source.

StatsBombSource is the only code that talks to statsbombpy, so it is the
only place ``sb`` gets mocked. Everything above it is tested with
InMemorySource instead.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from pitchside.data.source import CachedSource, StatsBombSource
from tests.support import CountingSource


# --- StatsBombSource ---------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize(("method", "args", "sb_call", "sb_kwargs"), [
    ("competitions", (), "competitions", {}),
    ("matches", (2, 44), "matches", {"competition_id": 2, "season_id": 44}),
    ("events", (12345,), "events", {"match_id": 12345}),
    ("lineups", (12345,), "lineups", {"match_id": 12345}),
])
def test_statsbomb_source_passes_ids_through_by_keyword(method, args, sb_call, sb_kwargs):
    sentinel = pd.DataFrame({"x": [1]})
    with patch(f"pitchside.data.source.sb.{sb_call}", return_value=sentinel) as mock_call:
        assert getattr(StatsBombSource(), method)(*args) is sentinel
    mock_call.assert_called_once_with(**sb_kwargs)


# --- CachedSource ------------------------------------------------------------

@pytest.fixture
def counting(frames_source) -> CountingSource:
    return CountingSource(frames_source)


@pytest.mark.unit
def test_cached_source_fetches_each_answer_once(counting):
    cached = CachedSource(counting)
    for _ in range(3):
        cached.competitions()
        cached.matches(2, 44)
        cached.events(12345)
        cached.lineups(12345)
    assert sorted(counting.calls) == sorted([
        ("competitions",), ("matches", 2, 44), ("events", 12345), ("lineups", 12345),
    ])


@pytest.mark.unit
def test_cached_source_keys_on_arguments(counting):
    cached = CachedSource(counting)
    cached.matches(2, 44)
    cached.matches(11, 90)
    cached.events(12345)
    cached.events(67890)
    assert len(counting.calls) == 4, "Different ids must not share a cache entry."


@pytest.mark.unit
def test_cached_source_instances_do_not_share_a_cache(counting):
    CachedSource(counting).events(12345)
    CachedSource(counting).events(12345)
    assert counting.calls == [("events", 12345)] * 2


@pytest.mark.unit
def test_cached_source_returns_the_same_frame(counting):
    cached = CachedSource(counting)
    assert cached.events(12345) is cached.events(12345)


@pytest.mark.unit
def test_cached_source_evicts_beyond_maxsize(counting):
    cached = CachedSource(counting, maxsize=1)
    cached.events(1)
    cached.events(2)
    cached.events(1)
    assert counting.calls.count(("events", 1)) == 2


# --- InMemorySource ----------------------------------------------------------

@pytest.mark.unit
def test_in_memory_source_unknown_ids_return_empty_frames(frames_source):
    assert frames_source.matches(999, 999).empty
    assert frames_source.events(999).empty
    assert frames_source.lineups(999) == {}
    assert "match_id" in frames_source.matches(999, 999).columns
