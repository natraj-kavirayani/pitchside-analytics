"""
Unit tests for pitchside.ui.motion.

Motion is declared as data, so these tests check rules about it that a
reviewer would otherwise have to eyeball: every animation names keyframes
that exist, nothing takes too long to settle, nothing runs for viewers
who asked their OS for reduced motion, and no animation can leave content
invisible. Whether the browser actually plays them is checked in
tests/e2e/test_motion.py.
"""

import pytest

from pitchside.ui.motion import (
    ABOUT_ITEM,
    ANIMATIONS,
    KEYFRAMES,
    MAX_SETTLE_MS,
    MORPH_MS,
    OVERVIEW_TRANSITIONS,
    PANEL,
    TRANSITIONS,
    Animation,
    Transition,
    motion_css,
)
from pitchside.ui.overview import CLOSED as OVERVIEW_CLOSED
from pitchside.ui.overview import STRIP as OVERVIEW_STRIP


@pytest.mark.unit
@pytest.mark.parametrize("animation", ANIMATIONS, ids=lambda a: a.selector)
def test_every_animation_uses_defined_keyframes(animation):
    assert animation.keyframes in KEYFRAMES


@pytest.mark.unit
def test_every_keyframes_block_is_used():
    used = {a.keyframes for a in ANIMATIONS}
    assert set(KEYFRAMES) == used, f"Unused keyframes: {set(KEYFRAMES) - used}"


@pytest.mark.unit
@pytest.mark.parametrize("animation", ANIMATIONS, ids=lambda a: a.selector)
def test_every_animation_settles_in_time(animation):
    assert 0 < animation.duration_ms
    assert animation.settle_ms <= MAX_SETTLE_MS, (
        f"{animation.selector} takes {animation.settle_ms}ms to settle; "
        f"keep motion under {MAX_SETTLE_MS}ms so it reads as feedback, not a wait."
    )


@pytest.mark.unit
@pytest.mark.parametrize("name", KEYFRAMES)
def test_keyframes_end_fully_visible_and_in_place(name):
    """Animations use fill mode "backwards", so after the last frame the
    element's own styles take over. If the last frame differed from them
    (anything but opacity 1 / no transform), content would visibly jump
    at the end."""
    final_frame = KEYFRAMES[name].split("to {")[1].rstrip(" }")
    declarations = (d.split(":", 1) for d in final_frame.split(";") if d.strip())
    end = {prop.strip(): value.strip() for prop, value in declarations}
    assert end, f"{name} has no final frame."
    assert end.get("opacity", "1") == "1"
    assert end.get("transform", "none") in {"none", "scaleX(1)", "scaleY(1)"}


@pytest.mark.unit
def test_tab_panel_has_an_entrance_animation():
    """The tab transition: Streamlit mounts a new panel per tab switch, so
    an animation on the panel replays on every switch."""
    panel = [a for a in ANIMATIONS if a.selector == PANEL]
    assert len(panel) == 1 and panel[0].keyframes == "ps-panel-in"


@pytest.mark.unit
@pytest.mark.parametrize("container", [f"{PANEL} >", ABOUT_ITEM])
def test_page_blocks_enter_in_order(container):
    """Tab panels and the About page both bring their blocks in one by one."""
    items = [a for a in ANIMATIONS if a.selector.startswith(container)]
    delays = [a.delay_ms for a in items]
    assert len(items) >= 2 and delays == sorted(delays) and len(set(delays)) == len(delays)


@pytest.mark.unit
def test_text_buttons_never_lift_on_hover():
    hover_rules = [line for line in motion_css().splitlines() if ":hover" in line and "button" in line]
    assert hover_rules and all(':not([kind="tertiary"])' in r for r in hover_rules if "transform" in r)


@pytest.mark.unit
def test_staggered_delay_uses_index_variable():
    css = Animation(".x", "ps-fade", 100, delay_ms=50, stagger_ms=30, max_index=2).css()
    assert "calc(50ms + var(--i, 0) * 30ms)" in css


@pytest.mark.unit
def test_settle_time_includes_the_last_staggered_item():
    assert Animation(".x", "ps-fade", 100, delay_ms=50, stagger_ms=30, max_index=4).settle_ms == 270


@pytest.mark.unit
def test_all_motion_is_inside_the_reduced_motion_guard():
    css = motion_css()
    assert css.startswith("<style>\n@media (prefers-reduced-motion: no-preference) {")
    assert css.endswith("}\n</style>")
    body = css.split("{", 1)[1]
    assert body.count("{") == body.count("}") - 1, "Braces must balance inside the media block."


@pytest.mark.unit
def test_css_contains_every_rule():
    css = motion_css()
    for name in KEYFRAMES:
        assert f"@keyframes {name} " in css
    for rule in (*ANIMATIONS, *TRANSITIONS):
        assert rule.css() in css


@pytest.mark.unit
def test_feedback_transitions_are_quick():
    """Hover and focus feedback has to feel instant."""
    feedback = [t for t in TRANSITIONS if t not in OVERVIEW_TRANSITIONS]
    assert feedback and all(t.settle_ms <= 300 for t in feedback)


@pytest.mark.unit
@pytest.mark.parametrize("transition", OVERVIEW_TRANSITIONS, ids=lambda t: t.selector)
def test_overview_transitions_settle_in_time(transition):
    assert 0 < transition.settle_ms <= MAX_SETTLE_MS


@pytest.mark.unit
def test_overview_box_changes_size_and_shape():
    """The strip shrinks into the pill (and the content below follows its
    height), rather than just fading out."""
    strip_rules = [t for t in OVERVIEW_TRANSITIONS if t.selector.endswith(OVERVIEW_STRIP)]
    assert len(strip_rules) == 2, "One timing for opening, one for closing."
    for rule in strip_rules:
        assert {"width", "height", "border-radius"} <= set(rule.properties)
        assert rule.settle_ms >= MORPH_MS


@pytest.mark.unit
def test_closing_hides_the_strip_only_after_it_has_shrunk():
    closing = next(t for t in OVERVIEW_TRANSITIONS if t.selector == f"{OVERVIEW_CLOSED} {OVERVIEW_STRIP}")
    assert "visibility 0ms" in closing.css() and f"{MORPH_MS}ms;" in closing.css()


@pytest.mark.unit
def test_transition_timing_overrides_one_property():
    t = Transition(".x", ("width", "opacity"), 400, timing=(("opacity", 100, 300),))
    assert "width 400ms" in t.css() and t.css().count("ms") == 3
    assert t.settle_ms == 400


@pytest.mark.unit
def test_entrance_animations_leave_properties_free_for_transitions():
    """Fill mode "both" would pin opacity/transform after the animation,
    and the overview's transitions would silently never run."""
    assert all(a.css().rstrip(" }").split(";")[0].endswith("backwards") for a in ANIMATIONS)


@pytest.mark.unit
def test_height_can_animate_to_and_from_auto():
    assert "interpolate-size: allow-keywords" in motion_css()
