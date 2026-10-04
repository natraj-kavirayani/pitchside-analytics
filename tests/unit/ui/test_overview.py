"""Unit tests for when the match overview is shown (pitchside.ui.overview)."""

import pytest

from pitchside.ui.overview import overview_open

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
