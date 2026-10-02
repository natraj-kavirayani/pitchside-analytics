"""
A small, deterministic, made-up league in StatsBomb's shape.

``SampleSource`` lets the app run with no network access (set
``PITCHSIDE_DATA_SOURCE=sample``), and gives the e2e smoke tests a fixed
dataset instead of a random live match. The same seed always produces the
same events, so tests can assert exact values.

The three matches cover the cases the app treats specially:

- an ordinary win,
- a draw decided by a penalty shootout (period 5 kicks),
- a goalless draw with a manager missing from the data.

Coordinates follow StatsBomb's convention: a 120 x 80 pitch with every
team attacking left to right.
"""

import random
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from pitchside.data.source import InMemorySource, Lineups

COMPETITION_ID = 9001
SEASON_ID = 1

# A 4-3-3: (position, base x, base y) per starter, goalkeeper first.
FORMATION = [
    ("Goalkeeper", 6, 40),
    ("Right Back", 35, 70), ("Right Center Back", 25, 52),
    ("Left Center Back", 25, 28), ("Left Back", 35, 10),
    ("Right Center Midfield", 55, 58), ("Center Defensive Midfield", 45, 40),
    ("Left Center Midfield", 55, 22),
    ("Right Wing", 85, 70), ("Center Forward", 95, 40), ("Left Wing", 85, 10),
]
SHOT_MISSES = ["Saved", "Off T", "Blocked", "Wayward", "Post"]

FIRST_NAMES = ["Alex", "Bruno", "Caio", "Dara", "Emeka", "Felix", "Goran", "Hugo", "Ivo",
               "Jonas", "Kofi", "Luca", "Mateo", "Nils", "Omar", "Pavel", "Quinn"]
LAST_NAMES = ["Abbott", "Barros", "Costa", "Doyle", "Eze", "Falk", "Gomez", "Haas", "Ito",
              "Jensen", "Kane", "Lund", "Moreau", "Novak", "O'Neill", "Pires", "Quist",
              "Reyes", "Silva", "Toure", "Ulloa", "Vidal", "Weber", "Xavier", "Young", "Zola"]


@dataclass(frozen=True)
class SampleMatch:
    match_id: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    match_date: str
    home_manager: str | None
    away_manager: str | None
    # Kicks per team in the order taken: True = scored. None = no shootout.
    shootout: tuple[tuple[bool, ...], tuple[bool, ...]] | None = None


MATCHES = [
    SampleMatch(900101, "Harbour Rovers", "Northgate United", 2, 1, "2026-08-15",
                "Ana Ferreira", "Tom Becker"),
    SampleMatch(900102, "Kingsford City", "Ashdown Athletic", 1, 1, "2026-08-22",
                "Lena Ortiz", "Sam Okafor",
                shootout=((True, True, False, True, True), (True, False, True, False))),
    SampleMatch(900103, "Northgate United", "Kingsford City", 0, 0, "2026-08-29",
                "Tom Becker", None),
]


@lru_cache(maxsize=1)
def _squads() -> dict[str, tuple[str, ...]]:
    """14 players per team (11 starters, then 3 substitutes).

    Names are unique across the whole league, not just within a team, so
    a player's name alone identifies them in every match.
    """
    rng = random.Random("squads")
    teams = sorted({t for m in MATCHES for t in (m.home_team, m.away_team)})
    used: set[str] = set()
    squads: dict[str, tuple[str, ...]] = {}
    for team in teams:
        names: list[str] = []
        while len(names) < 14:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            if name not in used:
                used.add(name)
                names.append(name)
        squads[team] = tuple(names)
    return squads


def _squad(team: str) -> list[str]:
    return list(_squads()[team])


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _near(rng: random.Random, x: float, y: float, spread: float) -> list[float]:
    return [round(_clamp(rng.gauss(x, spread), 0.5, 119.5), 1),
            round(_clamp(rng.gauss(y, spread), 0.5, 79.5), 1)]


def _team_events(rng: random.Random, team: str, goals: int) -> tuple[list[dict], list[dict]]:
    """Generate one team's in-match events and its substitutions."""
    squad = _squad(team)
    starters, bench = squad[:11], squad[11:]
    base = {name: (x, y) for name, (_, x, y) in zip(starters, FORMATION)}

    # Three substitutions, outfield players only, at distinct minutes.
    sub_minutes = sorted(rng.sample(range(58, 86), 3))
    off_players = rng.sample(starters[5:], 3)
    subs = [{"type": "Substitution", "team": team, "player": off, "minute": minute, "second": 0,
             "substitution_replacement": on, "period": 2, "location": None}
            for off, on, minute in zip(off_players, bench, sub_minutes)]
    replaced_at = {s["player"]: (s["minute"], s["substitution_replacement"]) for s in subs}
    for off, on in zip(off_players, bench):
        base[on] = base[off]

    def on_pitch(minute: int) -> list[str]:
        players = []
        for name in starters:
            if name in replaced_at and minute >= replaced_at[name][0]:
                players.append(replaced_at[name][1])
            else:
                players.append(name)
        return players

    events: list[dict] = []
    for _ in range(140):
        minute = rng.randrange(0, 90)
        players = on_pitch(minute)
        passer, recipient = rng.sample(players, 2)
        completed = rng.random() < 0.82
        events.append({
            "type": "Pass", "team": team, "player": passer, "minute": minute,
            "second": rng.randrange(60), "period": 1 if minute < 45 else 2,
            "location": _near(rng, *base[passer], spread=9),
            "pass_end_location": _near(rng, *base[recipient], spread=9),
            "pass_outcome": None if completed else "Incomplete",
            "pass_recipient": recipient,
        })

    shot_count = goals + rng.randrange(5, 11)
    goal_slots = set(rng.sample(range(shot_count), goals))
    for i in range(shot_count):
        minute = rng.randrange(1, 90)
        is_goal = i in goal_slots
        shooter = rng.choice([p for p in on_pitch(minute) if base[p][0] > 50])
        events.append({
            "type": "Shot", "team": team, "player": shooter, "minute": minute,
            "second": rng.randrange(60), "period": 1 if minute < 45 else 2,
            "location": [round(rng.uniform(96, 114), 1), round(rng.uniform(26, 54), 1)],
            "shot_outcome": "Goal" if is_goal else rng.choice(SHOT_MISSES),
            "shot_statsbomb_xg": round(rng.uniform(0.25, 0.6) if is_goal else rng.uniform(0.02, 0.25), 3),
        })
    return events, subs


def _shootout_events(match: SampleMatch) -> list[dict]:
    if match.shootout is None:
        return []
    events = []
    for team, kicks in ((match.home_team, match.shootout[0]), (match.away_team, match.shootout[1])):
        takers = list(reversed(_squad(team)[:11]))
        for kick, scored in enumerate(kicks):
            events.append({
                "type": "Shot", "team": team, "player": takers[kick], "period": 5,
                "minute": 120 + kick, "second": 0 if team == match.home_team else 30,
                "location": [108.0, 40.0], "shot_statsbomb_xg": 0.783,
                "shot_outcome": "Goal" if scored else "Saved",
            })
    # Teams alternate kicks, so interleave them in the order taken.
    return sorted(events, key=lambda e: (e["minute"], e["second"]))


def _events(match: SampleMatch) -> pd.DataFrame:
    rng = random.Random(match.match_id)
    home, home_subs = _team_events(rng, match.home_team, match.home_score)
    away, away_subs = _team_events(rng, match.away_team, match.away_score)
    rows = home + away + home_subs + away_subs
    rows.sort(key=lambda e: (e["period"], e["minute"], e["second"]))
    rows += _shootout_events(match)

    columns = ["index", "period", "minute", "second", "type", "team", "player", "location",
               "pass_end_location", "pass_outcome", "pass_recipient",
               "shot_outcome", "shot_statsbomb_xg", "substitution_replacement"]
    frame = pd.DataFrame(rows).reindex(columns=columns)
    frame["index"] = range(1, len(frame) + 1)
    return frame


def _lineups(match: SampleMatch, events: pd.DataFrame) -> Lineups:
    came_on = set(events.loc[events["type"] == "Substitution", "substitution_replacement"])
    result: Lineups = {}
    for team in (match.home_team, match.away_team):
        rows = []
        for i, name in enumerate(_squad(team)):
            if i < 11:
                positions = [{"position": FORMATION[i][0], "start_reason": "Starting XI"}]
            elif name in came_on:
                positions = [{"position": "Substitute", "start_reason": "Substitution - On"}]
            else:
                positions = []
            rows.append({"player_name": name, "jersey_number": i + 1, "positions": positions})
        result[team] = pd.DataFrame(rows)
    return result


class SampleSource(InMemorySource):
    """The sample league, built once per instance from fixed seeds."""

    def __init__(self) -> None:
        competitions = pd.DataFrame([{
            "competition_id": COMPETITION_ID, "season_id": SEASON_ID,
            "country_name": "Pitchside", "competition_name": "Sample League",
            "season_name": "Demo",
        }])
        matches = pd.DataFrame([{
            "match_id": m.match_id, "home_team": m.home_team, "away_team": m.away_team,
            "home_score": m.home_score, "away_score": m.away_score, "match_date": m.match_date,
            "home_managers": m.home_manager, "away_managers": m.away_manager,
        } for m in MATCHES])
        events = {m.match_id: _events(m) for m in MATCHES}
        super().__init__(
            competitions=competitions,
            matches={(COMPETITION_ID, SEASON_ID): matches},
            events=events,
            lineups={m.match_id: _lineups(m, events[m.match_id]) for m in MATCHES},
        )
