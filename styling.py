"""
styling.py
Custom look-and-feel for Pitchside Analytics: a hand-built SVG
logo, a color-gradient background, pill-shaped inputs/buttons, color-coded
tabs, and a custom font. All of this is plain CSS/HTML injected into the
page via st.markdown(unsafe_allow_html=True) - Streamlit doesn't have a
first-class theming API for this level of customization.

Important gotcha this file works around: Markdown treats a line indented
4+ spaces as a code block. If an f-string passed to st.markdown() has
leading indentation (easy to do by accident with a triple-quoted string
inside an indented function), the HTML gets shown as literal text instead
of being rendered. Every HTML string below is built with NO leading
whitespace on any line to avoid that trap.
"""

import textwrap

import streamlit as st

# A small hand-drawn logo: a stylised football on the left, a rising bar
# chart on the right (the "analytics" half of the name).
# Built as ONE line (no newlines/indentation) so it's safe to drop into
# other markdown strings without triggering the code-block trap above.
LOGO_SVG = (
    '<svg width="64" height="64" viewBox="0 0 120 100" xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="40" cy="50" r="32" fill="#f8fafc" stroke="#0f172a" stroke-width="3"/>'
    '<polygon points="40,28 51,36 47,49 33,49 29,36" fill="#0f172a"/>'
    '<polygon points="40,28 29,36 21,27 31,17" fill="none" stroke="#0f172a" stroke-width="2"/>'
    '<polygon points="40,28 51,36 59,27 49,17" fill="none" stroke="#0f172a" stroke-width="2"/>'
    '<polygon points="33,49 47,49 52,61 40,71 28,61" fill="none" stroke="#0f172a" stroke-width="2"/>'
    '<rect x="80" y="58" width="10" height="24" rx="3" fill="#22c55e"/>'
    '<rect x="94" y="42" width="10" height="40" rx="3" fill="#3b82f6"/>'
    '<rect x="108" y="24" width="8" height="58" rx="3" fill="#f59e0b"/>'
    '</svg>'
)


def apply_custom_style() -> None:
    """Inject the app's global CSS.

    Adds the gradient background, custom font, pill-shaped selectboxes and
    buttons, and colour-coded tab underlines. Call once, right after
    ``st.set_page_config()``, before any other page content.
    """
    css = textwrap.dedent("""
        <style>
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
        .stButton > button {
            border-radius: 999px !important;
            border: 1px solid #22c55e !important;
        }

        /* --- Color-coded tabs -------------------------------------------- */
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(1) { border-bottom: 3px solid #ef4444; }
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(2) { border-bottom: 3px solid #3b82f6; }
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(3) { border-bottom: 3px solid #22c55e; }
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(4) { border-bottom: 3px solid #f59e0b; }
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(5) { border-bottom: 3px solid #a855f7; }
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(6) { border-bottom: 3px solid #ec4899; }
        .stTabs [data-baseweb="tab-list"] button:nth-of-type(7) { border-bottom: 3px solid #14b8a6; }
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            color: #f8fafc !important;
            font-weight: 700;
        }
        </style>
    """).strip()
    st.markdown(css, unsafe_allow_html=True)


def render_header() -> None:
    """Render the page header: the SVG logo, the app title and a tagline."""
    html = (
        '<div style="display:flex; align-items:center; gap:16px; margin-bottom: 0.5rem;">'
        + LOGO_SVG +
        '<div>'
        '<h1 style="margin:0; color:#f8fafc;">Pitchside Analytics</h1>'
        '<p style="margin:0; color:#94a3b8; font-size:0.95rem;">'
        "Explore matches with StatsBomb's free open football data"
        '</p>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
