"""Test doubles shared across test layers."""

from pitchside.data.source import InMemorySource


class CountingSource(InMemorySource):
    """Records every call that reaches it."""

    def __init__(self, inner: InMemorySource) -> None:
        self.__dict__.update(inner.__dict__)
        self.calls: list[tuple] = []

    def competitions(self):
        self.calls.append(("competitions",))
        return super().competitions()

    def matches(self, competition_id, season_id):
        self.calls.append(("matches", competition_id, season_id))
        return super().matches(competition_id, season_id)

    def events(self, match_id):
        self.calls.append(("events", match_id))
        return super().events(match_id)

    def lineups(self, match_id):
        self.calls.append(("lineups", match_id))
        return super().lineups(match_id)
