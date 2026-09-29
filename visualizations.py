"""
visualizations.py
Plotting functions that turn StatsBomb event DataFrames into charts.

Every plot function returns a matplotlib Figure, so callers (Streamlit,
scripts, notebooks) can render or save it however they like. The penalty
shootout is a small table rather than a chart, so ``shootout_table_html``
returns an HTML string instead.
"""

from html import escape

import matplotlib.pyplot as plt
import pandas as pd
from mplsoccer import Pitch, VerticalPitch

SURFACE = "#1e1e1e"
INK = "#f8fafc"
MUTED_INK = "#94a3b8"
# Fixed order for two-team charts: first team alphabetically gets blue,
# second gets amber - a pair that stays distinct under common colour
# vision deficiencies.
TEAM_COLORS = ("#3b82f6", "#f59e0b")


def _pitch() -> Pitch:
    """Dark-themed horizontal pitch in StatsBomb coordinates."""
    return Pitch(pitch_type="statsbomb", pitch_color=SURFACE, line_color="#c7d5cc")


def _vertical_pitch() -> VerticalPitch:
    """Dark-themed top-to-bottom pitch in StatsBomb coordinates.

    Takes the same x/y values as ``_pitch()``; mplsoccer handles the rotation.
    """
    return VerticalPitch(pitch_type="statsbomb", pitch_color=SURFACE, line_color="#c7d5cc")


def plot_shot_map(shots: pd.DataFrame, title: str = "Shot Map") -> plt.Figure:
    """Bubble map of shots: size = expected goals (xG), red = goal.

    Args:
        shots: Output of ``data_loader.get_shots()``; needs ``location`` and
            ``shot_outcome``, optionally ``shot_statsbomb_xg``.
        title: Chart title.
    """
    pitch = _pitch()
    fig, ax = pitch.draw(figsize=(10, 7))
    fig.set_facecolor(SURFACE)

    if shots.empty:
        ax.set_title("No shot data", color="white")
        return fig

    x = shots["location"].apply(lambda loc: loc[0])
    y = shots["location"].apply(lambda loc: loc[1])
    xg = shots.get("shot_statsbomb_xg", pd.Series(0.05, index=shots.index)).fillna(0.05)
    is_goal = shots["shot_outcome"] == "Goal"

    pitch.scatter(
        x[~is_goal], y[~is_goal],
        s=(xg[~is_goal] * 900) + 60,
        color=MUTED_INK, edgecolors="black", alpha=0.7, ax=ax, label="No goal"
    )
    pitch.scatter(
        x[is_goal], y[is_goal],
        s=(xg[is_goal] * 900) + 60,
        color="#ef4444", edgecolors="black", alpha=0.9, ax=ax, label="Goal"
    )
    ax.legend(facecolor=SURFACE, labelcolor="white", loc="upper left")
    ax.set_title(title, color="white", fontsize=14)
    return fig


def plot_pass_map(passes: pd.DataFrame, title: str = "Pass Map") -> plt.Figure:
    """Arrows from each pass's start to end location; green = completed, red = not.

    Args:
        passes: Output of ``data_loader.get_passes()``; needs ``location``,
            ``pass_end_location`` and ``pass_outcome``.
        title: Chart title.
    """
    pitch = _pitch()
    fig, ax = pitch.draw(figsize=(10, 7))
    fig.set_facecolor(SURFACE)

    if passes.empty:
        ax.set_title("No pass data", color="white")
        return fig

    x_start = passes["location"].apply(lambda loc: loc[0])
    y_start = passes["location"].apply(lambda loc: loc[1])
    x_end = passes["pass_end_location"].apply(lambda loc: loc[0])
    y_end = passes["pass_end_location"].apply(lambda loc: loc[1])
    completed = passes["pass_outcome"].isna()  # NaN outcome = completed in StatsBomb data

    pitch.arrows(
        x_start[completed], y_start[completed], x_end[completed], y_end[completed],
        color="#22c55e", ax=ax, width=1.5, headwidth=4, label="Completed"
    )
    pitch.arrows(
        x_start[~completed], y_start[~completed], x_end[~completed], y_end[~completed],
        color="#ef4444", ax=ax, width=1.5, headwidth=4, alpha=0.6, label="Incomplete"
    )
    ax.legend(facecolor=SURFACE, labelcolor="white", loc="upper left")
    ax.set_title(title, color="white", fontsize=14)
    return fig


def plot_heatmap(events: pd.DataFrame, title: str = "Touch Heatmap") -> plt.Figure:
    """Density (KDE) heatmap of where on the pitch events happened.

    Args:
        events: Any event DataFrame with a ``location`` column.
        title: Chart title.
    """
    pitch = _pitch()
    fig, ax = pitch.draw(figsize=(10, 7))
    fig.set_facecolor(SURFACE)

    located = events.dropna(subset=["location"])
    if located.empty:
        ax.set_title("No location data", color="white")
        return fig

    x = located["location"].apply(lambda loc: loc[0])
    y = located["location"].apply(lambda loc: loc[1])

    pitch.kdeplot(x, y, ax=ax, fill=True, cmap="Reds", levels=100, alpha=0.8)
    ax.set_title(title, color="white", fontsize=14)
    return fig


def plot_pass_network(nodes: pd.DataFrame, edges: pd.DataFrame, title: str = "Pass Network") -> plt.Figure:
    """Team pass network on a vertical pitch.

    Each player is drawn at their average position, sized by passes made,
    with lines to teammates whose thickness reflects how often that pair
    combined.

    Args:
        nodes: ``player``, ``x``, ``y``, ``passes`` from
            ``data_loader.get_pass_network()``.
        edges: ``x1``, ``y1``, ``x2``, ``y2``, ``count`` from the same call.
        title: Chart title.
    """
    pitch = _vertical_pitch()
    fig, ax = pitch.draw(figsize=(7, 10))
    fig.set_facecolor(SURFACE)

    if nodes.empty:
        ax.set_title("No pass data", color="white")
        return fig

    max_count = edges["count"].max() if not edges.empty else 1
    for _, row in edges.iterrows():
        pitch.lines(
            row["x1"], row["y1"], row["x2"], row["y2"],
            lw=1 + (row["count"] / max_count) * 6,
            color=MUTED_INK, alpha=0.5, ax=ax, zorder=1,
        )

    max_passes = nodes["passes"].max()
    sizes = 300 + (nodes["passes"] / max_passes) * 900
    pitch.scatter(
        nodes["x"], nodes["y"], s=sizes,
        color="#3b82f6", edgecolors="black", ax=ax, zorder=2,
    )

    for _, row in nodes.iterrows():
        last_name = str(row["player"]).split(" ")[-1]
        pitch.annotate(
            last_name, xy=(row["x"], row["y"]), ax=ax,
            color="white", fontsize=8, fontweight="bold",
            ha="center", va="center", zorder=3,
        )

    ax.set_title(title, color="white", fontsize=14)
    return fig


def plot_xg_timeline(timeline: pd.DataFrame, title: str = "xG timeline") -> plt.Figure:
    """Step chart of each team's cumulative expected goals over the match.

    Goals are marked with a larger ringed dot. Each line ends in a direct
    label with the team's name and total xG, and a legend is also shown,
    so team identity never relies on colour alone.

    Args:
        timeline: Output of ``data_loader.get_xg_timeline()``.
        title: Chart title.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#475569")
    ax.tick_params(colors=MUTED_INK)
    ax.grid(axis="y", color="#334155", linewidth=0.6)
    ax.set_axisbelow(True)

    if timeline.empty:
        ax.set_title("No shot data", color="white")
        return fig

    end_minute = max(90.0, float(timeline["minute"].max()))
    for color, (team, rows) in zip(TEAM_COLORS, timeline.groupby("team", sort=True)):
        # Extend each line to full time so both teams' totals line up on the right.
        minutes = list(rows["minute"]) + [end_minute]
        cumulative = list(rows["cumulative_xg"]) + [rows["cumulative_xg"].iloc[-1]]
        ax.step(minutes, cumulative, where="post", color=color, linewidth=2, label=team)

        goals = rows[rows["is_goal"].astype(bool)]
        ax.scatter(
            goals["minute"], goals["cumulative_xg"], s=90, color=color,
            edgecolors=SURFACE, linewidths=2, zorder=3,
        )
        ax.annotate(
            f"{team}  {cumulative[-1]:.2f}", xy=(end_minute, cumulative[-1]),
            xytext=(6, 0), textcoords="offset points", va="center",
            color=INK, fontsize=9,
        )

    ax.set_xlim(0, end_minute)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Minute", color=MUTED_INK)
    ax.set_ylabel("Cumulative xG", color=MUTED_INK)
    ax.legend(facecolor=SURFACE, edgecolor="#475569", labelcolor="white", loc="upper left")
    ax.set_title(title, color="white", fontsize=14, loc="left")
    fig.tight_layout()
    return fig


def shootout_table_html(shootout: pd.DataFrame) -> str:
    """Render a penalty shootout as an HTML table, one row per team.

    Each kick is a check mark (scored) or a red circle (missed); hovering
    over it shows the taker's name via the cell's ``title`` attribute. The
    team that kicked first is on top, and each team name gets the same
    colour dot as its line on the xG timeline.

    The string has no leading whitespace or line breaks, so st.markdown()
    renders it as HTML rather than a Markdown code block.

    Args:
        shootout: Output of ``data_loader.get_shootout()``.
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
