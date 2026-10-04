"""
Unit tests for pitchside.ui.theme.

The CSS and header are plain strings, so most checks need no Streamlit.
Every assertion looks for a specific, named piece of CSS/HTML rather than
just "did it run": a missing font rule, icon override or logo should fail.

What these tests cannot see is whether a selector still matches
Streamlit's DOM after an upgrade (the old tab colours silently stopped
working that way). tests/e2e/test_motion.py checks computed styles in a
real browser for that.
"""

import pytest
from streamlit.testing.v1 import AppTest

from pitchside.ui.theme import LOGO_SVG, TAB, header_html, tab_accent_css, theme_css

ACCENTS = ["#ef4444", "#3b82f6", "#22c55e"]


@pytest.fixture
def css() -> str:
    return theme_css(ACCENTS)


@pytest.mark.unit
def test_css_starts_with_no_leading_whitespace(css):
    # A leading-whitespace first line makes Markdown treat the whole block
    # as an indented code block instead of rendering the <style> tag.
    assert css.splitlines()[0] == "<style>"
    assert css.splitlines()[-1] == "</style>"


@pytest.mark.unit
def test_css_declares_custom_font(css):
    assert "'Aptos Mono'" in css, "Custom font-family declaration is missing from the injected CSS."


@pytest.mark.unit
def test_css_restores_icon_font_for_icon_elements(css):
    assert '[data-testid="stIconMaterial"]' in css, (
        "Icon-font override rule is missing; the sidebar collapse icon "
        "and other Material icons will render as raw text (e.g. "
        "'keyboard_double_arrow_right') instead of a glyph."
    )
    assert "Material Symbols" in css, "Icon font family is missing from the icon override rule."


@pytest.mark.unit
def test_css_has_pill_shaped_inputs_and_buttons(css):
    assert css.count("border-radius: 999px") == 2, (
        "Expected pill-shaped border-radius rules for both selectboxes and buttons."
    )


@pytest.mark.unit
def test_text_buttons_are_not_pills(css):
    """The About/Back links are text buttons; the pill border would make
    them look like the Shuffle button."""
    assert '.stButton > button:not([kind="tertiary"]) {' in css
    assert '.stButton > button[kind="tertiary"] {' in css


@pytest.mark.unit
def test_css_has_gradient_background(css):
    assert "linear-gradient" in css, "Gradient background rule is missing."


@pytest.mark.unit
def test_tab_accents_one_rule_per_tab_in_order():
    css = tab_accent_css(ACCENTS)
    for i, color in enumerate(ACCENTS, 1):
        assert f"{TAB}:nth-child({i}) {{ --ps-accent: {color}; }}" in css
    assert f"nth-child({len(ACCENTS) + 1})" not in css


@pytest.mark.unit
def test_tab_accents_target_react_aria_tabs_not_baseweb():
    """Streamlit 1.64 replaced baseweb tabs with react-aria ones; rules
    on [data-baseweb="tab-list"] stopped matching anything."""
    css = tab_accent_css(ACCENTS)
    assert "data-baseweb" not in css
    assert '[role="tab"]' in css and ".react-aria-SelectionIndicator" in css


@pytest.mark.unit
def test_header_contains_animated_logo_and_title():
    html = header_html()
    assert LOGO_SVG in html
    assert html.count('class="ps-logo-bar"') == 3
    assert 'class="ps-logo-ball"' in html
    assert "Pitchside Analytics" in html


@pytest.mark.unit
def test_header_html_is_a_single_line():
    assert "\n" not in header_html()


_SCRIPT = """
from pitchside.ui import theme

theme.apply_theme(["#ef4444"])
theme.render_header()
"""


@pytest.mark.unit
def test_streamlit_renders_style_then_header():
    at = AppTest.from_string(_SCRIPT, default_timeout=10).run()
    assert not at.exception
    assert [m.value[:6] for m in at.markdown] == ["<style", "<div c"]
