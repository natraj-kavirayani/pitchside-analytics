"""
Where match data comes from.

Everything above this layer depends only on the ``MatchDataSource``
protocol, so the app can run on StatsBomb's live open data, on the
offline sample (``pitchside.data.sample``), or on hand-built frames in a
test, without patching module globals.

statsbombpy types its fetchers as returning ``DataFrame | dict`` because a
``fmt`` parameter can switch the output to raw dicts. It is never passed
here, so the result is always a DataFrame; ``typing.cast`` records that
for the type checker without silencing real errors elsewhere.
"""

from collections.abc import Callable, Mapping
from functools import lru_cache
from typing import Protocol, cast

import pandas as pd
from statsbombpy import sb

Lineups = dict[str, pd.DataFrame]


class MatchDataSource(Protocol):
    """The four raw fetches the app needs. Implementations must not
    mutate frames they have already returned: callers may share them."""

    def competitions(self) -> pd.DataFrame:
        """One row per competition+season (see ``schema.COMPETITION_COLUMNS``)."""
        ...

    def matches(self, competition_id: int, season_id: int) -> pd.DataFrame:
        """One row per match in a competition/season (see ``schema.MATCH_COLUMNS``)."""
        ...

    def events(self, match_id: int) -> pd.DataFrame:
        """One row per event in a match (see ``schema.EVENT_COLUMNS``)."""
        ...

    def lineups(self, match_id: int) -> Lineups:
        """Squad per team, keyed by team name (see ``schema.LINEUP_COLUMNS``)."""
        ...


class StatsBombSource:
    """StatsBomb's free open data, fetched from their public GitHub repo.

    No API key is needed, but only certain competitions/seasons are
    available. See https://github.com/statsbomb/open-data.
    """

    def competitions(self) -> pd.DataFrame:
        return cast(pd.DataFrame, sb.competitions())

    def matches(self, competition_id: int, season_id: int) -> pd.DataFrame:
        return cast(pd.DataFrame, sb.matches(competition_id=competition_id, season_id=season_id))

    def events(self, match_id: int) -> pd.DataFrame:
        return cast(pd.DataFrame, sb.events(match_id=match_id))

    def lineups(self, match_id: int) -> Lineups:
        return cast(Lineups, sb.lineups(match_id=match_id))


class InMemorySource:
    """A source backed by frames already in memory.

    Used by the offline sample and by tests. Unknown ids behave like
    StatsBomb's own "nothing here" answers: no matches, no events.
    """

    def __init__(
        self,
        competitions: pd.DataFrame,
        matches: Mapping[tuple[int, int], pd.DataFrame],
        events: Mapping[int, pd.DataFrame],
        lineups: Mapping[int, Lineups] | None = None,
    ) -> None:
        self._competitions = competitions
        self._matches = dict(matches)
        self._events = dict(events)
        self._lineups = dict(lineups or {})

    def competitions(self) -> pd.DataFrame:
        return self._competitions

    def matches(self, competition_id: int, season_id: int) -> pd.DataFrame:
        empty = pd.DataFrame(columns=["match_id", "home_team", "away_team", "home_score",
                                      "away_score", "match_date"])
        return self._matches.get((competition_id, season_id), empty)

    def events(self, match_id: int) -> pd.DataFrame:
        return self._events.get(match_id, pd.DataFrame(columns=["type", "team", "player"]))

    def lineups(self, match_id: int) -> Lineups:
        return self._lineups.get(match_id, {})


class CachedSource:
    """Wraps another source and remembers each answer.

    The cache belongs to this instance, not the module, so two instances
    (e.g. two tests) never see each other's data.
    """

    def __init__(self, source: MatchDataSource, maxsize: int = 32) -> None:
        self.source = source
        self.competitions: Callable[[], pd.DataFrame] = lru_cache(maxsize=1)(source.competitions)
        self.matches: Callable[[int, int], pd.DataFrame] = lru_cache(maxsize=maxsize)(source.matches)
        self.events: Callable[[int], pd.DataFrame] = lru_cache(maxsize=maxsize)(source.events)
        self.lineups: Callable[[int], Lineups] = lru_cache(maxsize=maxsize)(source.lineups)
