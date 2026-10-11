"""Unit tests for when the match overview is shown (pitchside.ui.overview)."""

import pytest

from pitchside.ui.overview import CLOSED, LAYOUT_CSS, OPEN, PILL, STRIP, overview_open, state_marker

# A sidebar selection: the match plus the picker values that led to it.
PICK, OTHER_PICK = (1, ("pick_match", "Random")), (1, ("pick_match", "A 1 - 0 B"))
TAB, OTHER_TAB = "Shot map", "Pass map"


@pytest.mark.unit
def test_first_run_shows_the_overview():
    assert overview_open(was_open=False, previous_selection=None, selection=PICK, previous_view=None, view=TAB)


@pytest.mark.unit
@pytest.mark.parametrize("was_open", [True, False])
def test_any_new_selection_shows_the_overview(was_open):
    """Even one that lands on the match already shown, e.g. choosing the
    current random match by name."""
    assert overview_open(was_open, PICK, OTHER_PICK, TAB, TAB)


@pytest.mark.unit
def test_new_match_wins_over_a_tab_change():
    """Picking a match while on another tab still shows its overview."""
    assert overview_open(False, PICK, OTHER_PICK, TAB, OTHER_TAB)


@pytest.mark.unit
@pytest.mark.parametrize("was_open", [True, False])
def test_moving_to_another_tab_hides_the_overview(was_open):
    assert not overview_open(was_open, PICK, PICK, TAB, OTHER_TAB)


@pytest.mark.unit
@pytest.mark.parametrize("was_open", [True, False])
def test_other_reruns_leave_it_as_it_was(was_open):
    """E.g. a widget inside the tab, or the button having just reopened it."""
    assert overview_open(was_open, PICK, PICK, TAB, TAB) is was_open


@pytest.mark.unit
@pytest.mark.parametrize(("is_open", "value"), [(True, "true"), (False, "false")])
def test_state_marker_is_hidden_and_carries_the_state(is_open, value):
    marker = state_marker(is_open)
    assert f'data-open="{value}"' in marker and " hidden" in marker
    assert "\n" not in marker


def _rule(selector: str) -> str:
    """The declarations of the LAYOUT_CSS rule for ``selector``."""
    return LAYOUT_CSS.split(selector + " {", 1)[1].split("}", 1)[0]


@pytest.mark.unit
def test_closed_strip_takes_exactly_the_pills_size():
    """The strip shrinks into the pill, so the two must end the same size,
    or the box would jump at the end of the animation."""
    pill = _rule(f"{PILL} button")
    closed = _rule(f"{CLOSED} {STRIP}")
    for size in ("var(--ps-pill-w)", "var(--ps-pill-h)"):
        assert size in pill and size in closed


@pytest.mark.unit
def test_parts_share_one_grid_cell():
    """Stacked in one cell, the container is as tall as the strip, so the
    content below follows the strip's height as it changes."""
    assert "grid-area: 1 / 1" in LAYOUT_CSS
    assert "grid-template-columns: minmax(0, 1fr)" in LAYOUT_CSS


@pytest.mark.unit
def test_hidden_parts_cannot_be_clicked_or_focused():
    assert "visibility: hidden" in _rule(f"{OPEN} {PILL}")
    assert "visibility: hidden" in _rule(f"{CLOSED} {STRIP}")
