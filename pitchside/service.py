"""
The app's single entry point to match data.

``MatchService`` composes a ``MatchDataSource`` (where the data comes
from) with the pure functions in ``pitchside.analytics`` (what is computed
from it). The UI only talks to this class, so swapping the source (live,
sample, or a test's in-memory frames) needs no change anywhere else.
"""

import os
from dataclasses import dataclass

import pandas as pd

from pitchside.analytics import lineups, passing, shots, summary
from pitchside.data.source import CachedSource, MatchDataSource, StatsBombSource

DATA_SOURCE_ENV = "PITCHSIDE_DATA_SOURCE"


@dataclass(frozen=True)
class MatchRef:
    """One match in a competition/season: who played, the score and when."""

    competition_id: int
    season_id: int
    match_id: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    match_date: str

    @property
    def label(self) -> str:
        """"Home 2 - 1 Away (date)", as shown in the match dropdown."""
        return (f"{self.home_team} {self.home_score} - {self.away_score} "
                f"{self.away_team} ({self.match_date})")


class MatchService:
    """Match data and the analytics built on it, for one data source."""

    def __init__(self, source: MatchDataSource, label: str = "custom data source") -> None:
        self.source = source
        self.label = label  # where the data comes from, shown in the sidebar

    # --- Browsing -------------------------------------------------------

    def competitions(self) -> pd.DataFrame:
        return self.source.competitions()

    def matches(self, competition_id: int, season_id: int) -> list[MatchRef]:
        """Every match in a competition/season, in the source's order."""
        frame = self.source.matches(competition_id, season_id)
        return [
            MatchRef(
                competition_id=competition_id, season_id=season_id,
                match_id=int(row["match_id"]),
                home_team=str(row["home_team"]), away_team=str(row["away_team"]),
                home_score=int(row["home_score"]), away_score=int(row["away_score"]),
                match_date=str(row["match_date"]),
            )
            for _, row in frame.iterrows()
        ]

    # --- One match --------------------------------------------------------

    def events(self, match_id: int) -> pd.DataFrame:
        return self.source.events(match_id)

    def teams(self, match_id: int) -> list[str]:
        return shots.teams(self.events(match_id))

    def shots(self, match_id: int, team: str | None = None) -> pd.DataFrame:
        return shots.match_shots(self.events(match_id), team=team)

    def shootout(self, match_id: int) -> pd.DataFrame:
        return shots.shootout(self.events(match_id))

    def xg_timeline(self, match_id: int) -> pd.DataFrame:
        return shots.xg_timeline(self.events(match_id))

    def passes(self, match_id: int, team: str | None = None, player: str | None = None) -> pd.DataFrame:
        return passing.passes(self.events(match_id), team=team, player=player)

    def passers(self, match_id: int) -> list[str]:
        return passing.passers(self.events(match_id))

    def pass_network(
        self, match_id: int, team: str, until_first_sub: bool = True,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        return passing.pass_network(self.events(match_id), team, until_first_sub=until_first_sub)

    def starting_xi(self, match_id: int) -> dict[str, pd.DataFrame]:
        return lineups.starting_xi(self.source.lineups(match_id))

    def substitutions(self, match_id: int) -> pd.DataFrame:
        return lineups.substitutions(self.events(match_id))

    def managers(self, match: MatchRef) -> dict[str, str]:
        return lineups.managers(self.source.matches(match.competition_id, match.season_id),
                                match.match_id)

    def summary(self, match_id: int) -> pd.DataFrame:
        return summary.team_summary(self.events(match_id))


def build_service(kind: str | None = None) -> MatchService:
    """Create the service for a data source kind, with caching.

    Args:
        kind: ``"statsbomb"`` (live open data) or ``"sample"`` (the offline
            sample league). Defaults to the ``PITCHSIDE_DATA_SOURCE``
            environment variable, then ``"statsbomb"``.
    """
    kind = (kind or os.environ.get(DATA_SOURCE_ENV) or "statsbomb").strip().lower()
    if kind == "statsbomb":
        return MatchService(CachedSource(StatsBombSource()), label="StatsBomb open data")
    if kind == "sample":
        from pitchside.data.sample import SampleSource  # only built when asked for
        return MatchService(SampleSource(), label="offline sample league")
    raise ValueError(f"Unknown {DATA_SOURCE_ENV} {kind!r}: expected 'statsbomb' or 'sample'.")
