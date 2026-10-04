"""Unit tests for the view registry (pitchside.ui.views.VIEWS)."""

import re

import pytest

from pitchside.ui.views import VIEWS


@pytest.mark.unit
def test_view_labels_are_unique():
    labels = [v.label for v in VIEWS]
    assert len(labels) == len(set(labels))


@pytest.mark.unit
def test_view_accents_are_distinct_hex_colours():
    accents = [v.accent for v in VIEWS]
    assert all(re.fullmatch(r"#[0-9a-f]{6}", a) for a in accents)
    assert len(set(accents)) == len(accents), "Two tabs with one colour can't be told apart."


@pytest.mark.unit
def test_every_view_has_a_renderer():
    assert all(callable(v.render) for v in VIEWS)


@pytest.mark.unit
def test_about_is_a_page_not_a_tab():
    assert "About" not in {v.label for v in VIEWS}
