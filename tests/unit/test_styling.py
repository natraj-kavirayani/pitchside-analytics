"""
Unit tests for styling.py.

apply_custom_style() and render_header() both call Streamlit functions
directly, so they're exercised through AppTest rather than called as plain
Python functions. Every assertion here checks for a specific, named piece
of CSS/HTML rather than just "did it run without an exception" - a missing
font rule, icon override, or logo should fail the test, not pass silently.
"""

import pytest
from streamlit.testing.v1 import AppTest

_SCRIPT = """
import styling

styling.apply_custom_style()
styling.render_header()
"""


@pytest.fixture
def rendered_style_and_header():
    at = AppTest.from_string(_SCRIPT, default_timeout=10).run()
    assert not at.exception
    assert len(at.markdown) == 2, (
        "Expected exactly two markdown blocks: the injected <style> CSS and "
        "the header HTML."
    )
    return at.markdown[0].value, at.markdown[1].value


@pytest.mark.unit
def test_css_starts_with_no_leading_whitespace(rendered_style_and_header):
    css, _ = rendered_style_and_header
    # A leading-whitespace first line makes Markdown treat the whole block
    # as an indented code block instead of rendering the <style> tag.
    assert css.splitlines()[0] == "<style>"


@pytest.mark.unit
def test_css_declares_custom_font(rendered_style_and_header):
    css, _ = rendered_style_and_header
    assert "'Aptos Mono'" in css, "Custom font-family declaration is missing from the injected CSS."


@pytest.mark.unit
def test_css_restores_icon_font_for_icon_elements(rendered_style_and_header):
    css, _ = rendered_style_and_header
    assert '[data-testid="stIconMaterial"]' in css, (
        "Icon-font override rule is missing; the sidebar collapse icon "
        "and other Material icons will render as raw text (e.g. "
        "'keyboard_double_arrow_right') instead of a glyph."
    )
    assert "Material Symbols" in css, "Icon font family is missing from the icon override rule."


@pytest.mark.unit
def test_css_has_pill_shaped_inputs_and_buttons(rendered_style_and_header):
    css, _ = rendered_style_and_header
    assert css.count("border-radius: 999px") == 2, (
        "Expected pill-shaped border-radius rules for both selectboxes and buttons."
    )


@pytest.mark.unit
def test_css_has_gradient_background(rendered_style_and_header):
    css, _ = rendered_style_and_header
    assert "linear-gradient" in css, "Gradient background rule is missing."


@pytest.mark.unit
def test_css_has_one_color_coded_border_per_tab(rendered_style_and_header):
    css, _ = rendered_style_and_header
    # app.py renders 7 tabs (see app.TAB_LABELS; not imported here because
    # importing app.py runs the whole Streamlit script); each needs its own
    # colored underline rule.
    assert css.count("border-bottom: 3px solid") == 7


@pytest.mark.unit
def test_header_contains_logo_svg(rendered_style_and_header):
    _, header_html = rendered_style_and_header
    assert "<svg" in header_html and "</svg>" in header_html, "Logo SVG is missing from the header."


@pytest.mark.unit
def test_header_contains_title_text(rendered_style_and_header):
    _, header_html = rendered_style_and_header
    assert "Pitchside Analytics" in header_html


@pytest.mark.unit
def test_header_html_has_no_leading_whitespace(rendered_style_and_header):
    _, header_html = rendered_style_and_header
    for i, line in enumerate(header_html.splitlines()):
        assert not line.startswith((" ", "\t")), (
            f"Header HTML line {i} ('{line[:40]}...') has leading whitespace, "
            "which Markdown renders as a literal code block instead of HTML."
        )
