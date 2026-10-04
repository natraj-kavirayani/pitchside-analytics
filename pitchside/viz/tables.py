"""
HTML tables, for data that reads better as a table than a chart.

The strings have no leading whitespace or line breaks, so st.markdown()
renders them as HTML rather than a Markdown code block.
"""

from html import escape

import pandas as pd

from pitchside.viz.palette import INK, MUTED_INK, SURFACE, TEAM_COLORS


def shootout_table_html(shootout: pd.DataFrame) -> str:
    """Render a penalty shootout as an HTML table, one row per team.

    Each kick is a check mark (scored) or a red circle (missed); hovering
    over it shows the taker's name via the cell's ``title`` attribute. The
    team that kicked first is on top, and each team name gets the same
    colour dot as its line on the xG timeline.

    The string has no leading whitespace or line breaks, so st.markdown()
    renders it as HTML rather than a Markdown code block.

    Args:
        shootout: Output of ``pitchside.analytics.shots.shootout()``.
    """
    if shootout.empty:
        return ""

    team_colors = dict(zip(sorted(shootout["team"].unique()), TEAM_COLORS))
    kicks = int(shootout["kick"].max())
    cell = "padding:6px 10px; border-bottom:1px solid #334155; text-align:center;"

    header = "".join(f'<th style="{cell} color:{MUTED_INK};">{k}</th>' for k in range(1, kicks + 1))
    rows = []
    for team in shootout["team"].unique():  # order of first appearance = who kicked first
        team_kicks = shootout[shootout["team"] == team].set_index("kick")
        cells = []
        for k in range(1, kicks + 1):
            if k not in team_kicks.index:
                cells.append(f'<td style="{cell}"></td>')
                continue
            kick = team_kicks.loc[k]
            symbol, result = ("✅", "scored") if kick["scored"] else ("🔴", "missed")
            player = escape(str(kick["player"]), quote=True)
            cells.append(
                f'<td style="{cell} cursor:help;" title="{player}" '
                f'aria-label="{player} {result}">{symbol}</td>'
            )
        dot = f'<span style="color:{team_colors[team]};">●</span>'
        name = f'<td style="{cell} text-align:left; color:{INK}; white-space:nowrap;">{dot} {escape(team)}</td>'
        total = f'<td style="{cell} color:{INK}; font-weight:700;">{int(team_kicks["scored"].sum())}</td>'
        rows.append(f"<tr>{name}{''.join(cells)}{total}</tr>")

    return (
        f'<table style="border-collapse:collapse; background:{SURFACE}; border-radius:8px;">'
        f'<thead><tr><th style="{cell}"></th>{header}<th style="{cell} color:{MUTED_INK};">Total</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


# (label, column, format) for each row of the match summary strip.
SUMMARY_STATS = [
    ("xG", "xg", "{:.2f}"),
    ("Shots", "shots", "{:d}"),
    ("On target", "on_target", "{:d}"),
    ("Passes", "passes", "{:d}"),
    ("Pass completion", "pass_completion", "{:.0f}%"),
]


def split_share(left: float, right: float) -> float:
    """Return the left team's share of a two-team bar, as a percentage.

    An even 50/50 split when neither team has any (e.g. a 0-shot match),
    so the bar never collapses or divides by zero.
    """
    total = left + right
    if total <= 0:
        return 50.0
    # Clamped: float rounding can otherwise give e.g. 100.00000000000001.
    return min(100.0, max(0.0, 100.0 * left / total))


def summary_html(summary: pd.DataFrame) -> str:
    """Render two teams' headline numbers as a strip of split bars.

    Each row shows both teams' values with a bar split in proportion,
    coloured to match the xG timeline. The ``ps-*`` classes and the
    ``--i`` row index are hooks for the UI's entrance animation
    (``pitchside.ui.motion``); without it the strip is still complete.

    Args:
        summary: Output of ``pitchside.analytics.summary.team_summary()``.
            Anything other than exactly two teams renders nothing.
    """
    if len(summary) != 2:
        return ""
    left, right = summary.iloc[0], summary.iloc[1]
    left_color, right_color = TEAM_COLORS

    head = (
        f'<div style="display:flex; justify-content:space-between; color:{INK}; font-weight:700;">'
        f'<span><span style="color:{left_color};">●</span> {escape(str(left["team"]))}</span>'
        f'<span>{escape(str(right["team"]))} <span style="color:{right_color};">●</span></span>'
        "</div>"
    )
    rows = []
    for i, (label, column, fmt) in enumerate(SUMMARY_STATS):
        a, b = left[column], right[column]
        cast = float if "f" in fmt else int
        share = split_share(float(a), float(b))
        rows.append(
            f'<div class="ps-stat" style="--i:{i}; display:grid; gap:4px;">'
            f'<div style="display:flex; justify-content:space-between; color:{INK};">'
            f"<b>{fmt.format(cast(a))}</b>"
            f'<span style="color:{MUTED_INK}; font-size:0.85rem;">{label}</span>'
            f"<b>{fmt.format(cast(b))}</b></div>"
            f'<div style="display:flex; gap:3px; height:6px;">'
            f'<span class="ps-bar ps-bar-left" style="flex:0 0 calc({share:.1f}% - 1.5px); '
            f'background:{left_color}; border-radius:999px 0 0 999px;"></span>'
            f'<span class="ps-bar ps-bar-right" style="flex:1 1 0; '
            f'background:{right_color}; border-radius:0 999px 999px 0;"></span>'
            "</div></div>"
        )
    return (
        f'<div class="ps-summary" role="group" aria-label="Match summary" '
        f'style="display:grid; gap:10px; padding:14px 18px; margin:4px 0 12px; '
        f'background:rgba(15,23,42,0.55); border:1px solid #334155; border-radius:14px;">'
        f"{head}{''.join(rows)}</div>"
    )
