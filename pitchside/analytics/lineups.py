"""Starting XIs, substitutions and managers."""

import pandas as pd

from pitchside.data.source import Lineups

XI_COLUMNS = ["player", "jersey_number", "position"]
SUBSTITUTION_COLUMNS = ["team", "minute", "second", "player_off", "player_on"]
NOT_AVAILABLE = "Not available"


def starting_xi(lineups: Lineups) -> dict[str, pd.DataFrame]:
    """Return each team's starting XI and the position each player started in.

    Args:
        lineups: Output of ``MatchDataSource.lineups()``.

    Returns:
        Dict keyed by team name. Each DataFrame has columns ``player``,
        ``jersey_number`` and ``position``, sorted by jersey number.
    """
    result: dict[str, pd.DataFrame] = {}
    for team, df in lineups.items():
        rows: list[dict[str, object]] = []
        for _, row in df.iterrows():
            positions = row.get("positions") or []
            starters = [p for p in positions if p.get("start_reason") == "Starting XI"]
            if starters:
                rows.append({
                    "player": row["player_name"],
                    "jersey_number": row["jersey_number"],
                    "position": starters[0].get("position", ""),
                })
        xi_df = pd.DataFrame(rows, columns=XI_COLUMNS)
        if not xi_df.empty:
            xi_df = xi_df.sort_values("jersey_number").reset_index(drop=True)
        result[team] = xi_df
    return result


def substitutions(events: pd.DataFrame) -> pd.DataFrame:
    """Return a match's substitutions as a timeline.

    Returns:
        Columns ``team``, ``minute``, ``second``, ``player_off``,
        ``player_on``, one row per substitution sorted by time. Empty (but
        with those columns) if none were recorded.
    """
    subs = events[events["type"] == "Substitution"].copy()
    if subs.empty:
        return pd.DataFrame(columns=SUBSTITUTION_COLUMNS)
    sort_cols = ["minute", "second"] if "second" in subs.columns else ["minute"]
    subs = subs.sort_values(sort_cols)
    return pd.DataFrame({
        "team": subs["team"].values,
        "minute": subs["minute"].values,
        "second": subs["second"].values if "second" in subs.columns else 0,
        "player_off": subs["player"].values,
        "player_on": subs["substitution_replacement"].values
        if "substitution_replacement" in subs.columns else "Unknown",
    }).reset_index(drop=True)


def managers(matches: pd.DataFrame, match_id: int) -> dict[str, str]:
    """Return the home and away managers for a match.

    Args:
        matches: Output of ``MatchDataSource.matches()`` for the match's
            competition and season.

    Returns:
        ``{"home": ..., "away": ...}``, with "Not available" wherever the
        dataset has no manager recorded.
    """
    row = matches[matches["match_id"] == match_id]
    if row.empty:
        return {"home": NOT_AVAILABLE, "away": NOT_AVAILABLE}
    row = row.iloc[0]

    def _manager(col: str) -> str:
        # pandas stores a missing manager as NaN (truthy), not None, so a
        # plain `or "Not available"` fallback would render the string "nan".
        value = row.get(col)
        return NOT_AVAILABLE if value is None or pd.isna(value) or value == "" else str(value)

    return {"home": _manager("home_managers"), "away": _manager("away_managers")}
