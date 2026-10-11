"""
Static look-and-feel for Pitchside Analytics: a hand-built SVG logo, a
colour-gradient background, pill-shaped inputs/buttons, colour-coded tabs
and a custom font. Movement lives separately in ``pitchside.ui.motion``,
so it can be switched off without losing the theme.

All of this is plain CSS/HTML injected via st.markdown(unsafe_allow_html=True);
Streamlit has no first-class theming API for this level of customisation.
The selectors target Streamlit's rendered DOM (``data-testid`` attributes
and ARIA roles), which is not a public API and can change between
Streamlit versions. The e2e tests check the computed styles in a real
browser for that reason: unit tests can only see the CSS text.

Important gotcha this file works around: Markdown treats a line indented
4+ spaces as a code block. If an HTML string passed to st.markdown() has
leading indentation, it is shown as literal text instead of being
rendered. Every HTML string below is built with NO leading whitespace on
any line, and CSS blocks are dedented before use.
"""

import textwrap
from collections.abc import Sequence

import streamlit as st

from pitchside.ui.overview import LAYOUT_CSS as OVERVIEW_LAYOUT_CSS
from pitchside.viz.palette import INK, MUTED_INK

# A small hand-drawn logo: a stylised football on the left, a rising bar
# chart on the right (the "analytics" half of the name). The ps-logo-*
# classes and --i indexes are hooks for the entrance animation.
# Built as ONE line (no newlines/indentation) so it's safe to drop into
# other markdown strings without triggering the code-block trap above.
LOGO_SVG = (
    '<svg class="ps-logo" width="64" height="64" viewBox="0 0 120 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<g class="ps-logo-ball">'
    '<circle cx="40" cy="50" r="32" fill="#f8fafc" stroke="#0f172a" stroke-width="3"/>'
    '<polygon points="40,28 51,36 47,49 33,49 29,36" fill="#0f172a"/>'
    '<polygon points="40,28 29,36 21,27 31,17" fill="none" stroke="#0f172a" stroke-width="2"/>'
    '<polygon points="40,28 51,36 59,27 49,17" fill="none" stroke="#0f172a" stroke-width="2"/>'
    '<polygon points="33,49 47,49 52,61 40,71 28,61" fill="none" stroke="#0f172a" stroke-width="2"/>'
    '</g>'
    '<rect class="ps-logo-bar" style="--i:0" x="80" y="58" width="10" height="24" rx="3" fill="#22c55e"/>'
    '<rect class="ps-logo-bar" style="--i:1" x="94" y="42" width="10" height="40" rx="3" fill="#3b82f6"/>'
    '<rect class="ps-logo-bar" style="--i:2" x="108" y="24" width="8" height="58" rx="3" fill="#f59e0b"/>'
    '</svg>'
)

# Tabs are react-aria elements in Streamlit 1.64+: [role=tab] inside
# [data-testid=stTabs], with the active underline drawn by a
# .react-aria-SelectionIndicator child of the selected tab.
TAB = '[data-testid="stTabs"] [role="tab"]'
TAB_INDICATOR = ".react-aria-SelectionIndicator"

BASE_CSS = textwrap.dedent("""
    /* --- Font -----------------------------------------------------
       Aptos Mono ships with Microsoft Office/Windows, not the web, so
       there's no font file to load here. It's named first in the
       stack: browsers that have it installed locally (e.g. via MS
       Office) use it; everyone else falls back to a similar monospace
       font. */
    html, body, [class*="css"], [class*="st-"] {
        font-family: 'Aptos Mono', 'Consolas', 'SFMono-Regular', 'Courier New', monospace;
    }
    /* Streamlit renders icons (like the sidebar collapse arrow) as text
       such as "keyboard_double_arrow_right" that a special icon font
       turns into a glyph via ligatures. The broad font rule above was
       overriding that icon font too, so the raw text showed instead of
       the arrow. Restore the icon font specifically for those elements. */
    [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stExpandSidebarButton"] span,
    [data-testid="collapsedControl"] span,
    [class*="material-symbols"],
    [class*="material-icons"] {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
    }

    /* --- Background gradient --------------------------------------- */
    .stApp {
        background: linear-gradient(135deg, #0b3d2e 0%, #0f172a 55%, #1e1b4b 100%);
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }

    /* --- Pill-shaped selectboxes ------------------------------------ */
    div[data-baseweb="select"] > div {
        border-radius: 999px !important;
        border: 1px solid #3b82f6 !important;
    }

    /* --- Pill-shaped buttons ----------------------------------------- */
    .stButton > button:not([kind="tertiary"]) {
        border-radius: 999px !important;
        border: 1px solid #22c55e !important;
    }

    /* --- Text buttons (the About / Back links) ---------------------- */
    .stButton > button[kind="tertiary"] {
        color: #94a3b8;
        padding-left: 0;
        text-decoration: underline 1px transparent;
        text-underline-offset: 4px;
    }
    .stButton > button[kind="tertiary"]:hover {
        color: #f8fafc;
        text-decoration-color: #22c55e;
    }

    /* --- Charts ------------------------------------------------------ */
    [data-testid="stImage"] img {
        border-radius: 12px;
    }
""").strip()


def tab_accent_css(accents: Sequence[str]) -> str:
    """CSS giving each tab its own accent colour, in tab order.

    Each tab gets a faint underline in its colour, and the selected tab's
    indicator is drawn in full colour. The colour is set once per tab as
    the ``--ps-accent`` custom property, so the motion layer can reuse it.
    """
    rules = [
        f"{TAB} {{ --ps-accent: {MUTED_INK}; "
        "box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--ps-accent) 35%, transparent); }",
    ]
    rules += [f"{TAB}:nth-child({i}) {{ --ps-accent: {color}; }}" for i, color in enumerate(accents, 1)]
    rules += [
        f'{TAB}[aria-selected="true"] {{ color: {INK} !important; font-weight: 700; }}',
        f"{TAB}:hover {{ color: var(--ps-accent); }}",
        f"{TAB} {TAB_INDICATOR} {{ background-color: var(--ps-accent) !important; }}",
    ]
    return "\n".join(rules)


def theme_css(accents: Sequence[str]) -> str:
    """The full static stylesheet, as a ``<style>`` block for st.markdown()."""
    return f"<style>\n{BASE_CSS}\n{tab_accent_css(accents)}\n{OVERVIEW_LAYOUT_CSS}\n</style>"


def apply_theme(accents: Sequence[str]) -> None:
    """Inject the app's static CSS.

    Args:
        accents: One colour per tab, in tab order (see ``pitchside.ui.views``).
    """
    st.markdown(theme_css(accents), unsafe_allow_html=True)


def header_html() -> str:
    """The page header: the SVG logo, the app title and a tagline."""
    return (
        '<div class="ps-header" style="display:flex; align-items:center; gap:16px; margin-bottom: 0.5rem;">'
        + LOGO_SVG +
        '<div class="ps-title">'
        f'<h1 style="margin:0; color:{INK};">Pitchside Analytics</h1>'
        f'<p style="margin:0; color:{MUTED_INK}; font-size:0.95rem;">'
        "Explore matches with StatsBomb's free open football data"
        '</p>'
        '</div>'
        '</div>'
    )


def render_header() -> None:
    st.markdown(header_html(), unsafe_allow_html=True)
