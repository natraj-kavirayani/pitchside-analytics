"""Unit tests for the column contract helpers in pitchside.data.schema."""

import pandas as pd
import pytest

from pitchside.data.schema import (
    EVENT_COLUMNS,
    PASS_COLUMNS,
    SHOT_COLUMNS,
    SUBSTITUTION_COLUMNS,
    event_contract,
    missing_columns,
)


@pytest.mark.unit
def test_missing_columns_lists_only_what_is_absent():
    frame = pd.DataFrame(columns=["a", "b"])
    assert missing_columns(frame, frozenset({"a", "c"})) == {"c"}
    assert missing_columns(frame, frozenset({"a"})) == set()


@pytest.mark.unit
def test_event_contract_grows_with_the_event_types_present():
    assert event_contract(pd.DataFrame({"type": ["Pressure"]})) == EVENT_COLUMNS
    shots_and_subs = event_contract(pd.DataFrame({"type": ["Shot", "Substitution"]}))
    assert shots_and_subs == EVENT_COLUMNS | SHOT_COLUMNS | SUBSTITUTION_COLUMNS
    assert PASS_COLUMNS <= event_contract(pd.DataFrame({"type": ["Pass"]}))


@pytest.mark.unit
def test_event_contract_of_frame_without_type_column():
    assert event_contract(pd.DataFrame()) == EVENT_COLUMNS
