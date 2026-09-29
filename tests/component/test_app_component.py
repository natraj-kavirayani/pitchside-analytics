"""
Headless component tests for app.py via Streamlit's AppTest (st.testing.v1).

app.py is exercised as a whole, with every data_loader function it imports
mocked out - no test here reaches StatsBomb's open-data GitHub repository.
Patches target data_loader.<name> (not app.<name>): app.py's
`from data_loader import get_competitions, ...` statement re-executes on
every AppTest run, so it always picks up whatever data_loader.<name>
currently points to at run time.
"""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

# AppTest.from_file() resolves a relative path against the file that calls
# it (this file, in tests/component/), not the working directory pytest was
# invoked from - a bare "app.py" would look for tests/component/app.py and
# fail. Build an absolute path instead: this file is two directories below
# the project root, where app.py lives.
APP_PATH = str(Path(__file__).resolve().parent.parent.parent / "app.py")
SHOOTOUT_COLUMNS = ["team", "kick", "player", "scored"]


@pytest.fixture
def mock_starting_xi() -> dict[str, pd.DataFrame]:
    return {
        "Home Team": pd.DataFrame(
            [{"player": "Player A", "jersey_number": 10, "position": "Center Midfield"}]
        ),
        "Away Team": pd.DataFrame(
            [{"player": "Player X", "jersey_number": 7, "position": "Right Wing"}]
        ),
    }


@pytest.fixture
def mock_substitutions() -> pd.DataFrame:
    return pd.DataFrame([
        {"team": "Home Team", "minute": 60, "second": 0, "player_off": "Player A", "player_on": "Player C"},
    ])


@pytest.fixture
def mock_pass_network() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.DataFrame([{"player": "Player A", "x": 40.0, "y": 30.0, "passes": 5}])
    edges = pd.DataFrame(columns=["player", "pass_recipient", "count", "x1", "y1", "x2", "y2"])
    return nodes, edges


@pytest.fixture
def patched_app(
    mock_competitions_df,
    mock_matches_df,
    mock_events_df,
    mock_starting_xi,
    mock_substitutions,
    mock_pass_network,
):
    """Patch every data_loader function app.py calls, then run the app."""
    shots = mock_events_df[mock_events_df["type"] == "Shot"].copy()
    passes = mock_events_df[mock_events_df["type"] == "Pass"].copy()
    xg_timeline = pd.DataFrame([
        {"team": "Away Team", "minute": 0.0, "xg": 0.0, "cumulative_xg": 0.0, "is_goal": False, "player": None},
        {"team": "Away Team", "minute": 40.0, "xg": 0.08, "cumulative_xg": 0.08, "is_goal": False, "player": "Player Y"},
        {"team": "Home Team", "minute": 0.0, "xg": 0.0, "cumulative_xg": 0.0, "is_goal": False, "player": None},
        {"team": "Home Team", "minute": 30.25, "xg": 0.35, "cumulative_xg": 0.35, "is_goal": True, "player": "Player B"},
    ])

    with patch("data_loader.get_competitions", return_value=mock_competitions_df), \
         patch("data_loader.get_matches", return_value=mock_matches_df), \
         patch("data_loader.get_events", return_value=mock_events_df), \
         patch("data_loader.get_shots", return_value=shots), \
         patch("data_loader.get_passes", return_value=passes), \
         patch("data_loader.get_starting_xi", return_value=mock_starting_xi), \
         patch("data_loader.get_substitutions", return_value=mock_substitutions), \
         patch("data_loader.get_managers", return_value={"home": "Home Manager", "away": "Away Manager"}), \
         patch("data_loader.get_pass_network", return_value=mock_pass_network), \
         patch("data_loader.get_xg_timeline", return_value=xg_timeline), \
         patch("data_loader.get_shootout", return_value=pd.DataFrame(columns=SHOOTOUT_COLUMNS)):
        yield AppTest.from_file(APP_PATH, default_timeout=20).run()


@pytest.mark.component
def test_app_loads_without_exception(patched_app):
    at = patched_app
    assert not at.exception


@pytest.mark.component
def test_app_shows_title_and_sidebar_header(patched_app):
    at = patched_app
    # render_header() builds the title as raw HTML via st.markdown(), not
    # st.title(), so it shows up in at.markdown, not at.title.
    assert any("Pitchside Analytics" in m.value for m in at.markdown), (
        "Header title is missing from the rendered page."
    )
    assert any("Select a match" in h.value for h in at.sidebar.header), (
        "Sidebar header is missing."
    )


@pytest.mark.component
def test_app_renders_all_seven_tabs(patched_app):
    at = patched_app
    tab_labels = {t.label for t in at.tabs}
    assert tab_labels == {
        "Shot map", "xG timeline", "Pass map", "Pass network",
        "Touch heatmap", "Match details", "About",
    }


@pytest.mark.component
def test_app_renders_match_subheader(patched_app):
    at = patched_app
    assert len(at.subheader) == 1, "Expected exactly one subheader showing the selected match."
    assert " - " in at.subheader[0].value, "Match subheader should show a score line (e.g. '2 - 1')."


@pytest.mark.component
def test_app_renders_shot_and_pass_charts(patched_app):
    at = patched_app
    # AppTest models st.pyplot() output as an untyped element rather than a
    # distinct "pyplot" kind, so chart rendering is checked indirectly
    # through the captions app.py places directly below each chart - each
    # caption only exists if the st.pyplot() call above it ran without
    # raising.
    captions = {c.value for c in at.caption}
    assert any("Bubble size = expected goals" in c for c in captions), "Shot map chart/caption did not render."
    assert any("Each step is a shot" in c for c in captions), "xG timeline chart/caption did not render."
    assert any("Green = completed pass" in c for c in captions), "Pass map chart/caption did not render."
    assert any("Node position" in c for c in captions), "Pass network chart/caption did not render."


@pytest.mark.component
def test_app_renders_starting_xi_table(patched_app):
    at = patched_app
    assert len(at.dataframe) >= 1, "Expected at least the starting XI table to render."


@pytest.mark.component
def test_shuffle_button_is_present_and_clickable(patched_app):
    at = patched_app
    # The Match field defaults to "Random match", so the Shuffle button
    # must always be present on a fresh load - assert that explicitly
    # instead of silently skipping the click when it's missing, which
    # would let this test pass without testing anything.
    shuffle_buttons = [b for b in at.button if "Shuffle" in b.label]
    assert shuffle_buttons, "Expected a 'Shuffle random match' button on initial load."

    at = shuffle_buttons[0].click().run()
    assert not at.exception


@pytest.mark.component
def test_no_matches_for_selection_stops_with_warning(
    mock_competitions_df, mock_events_df,
):
    empty_matches = pd.DataFrame(columns=["match_id", "home_team", "away_team", "home_score", "away_score", "match_date"])
    with patch("data_loader.get_competitions", return_value=mock_competitions_df), \
         patch("data_loader.get_matches", return_value=empty_matches):
        at = AppTest.from_file(APP_PATH, default_timeout=20).run()
        assert any("No matches found" in w.value for w in at.warning), (
            "Expected a warning when the selected competition/season has no matches."
        )


@pytest.mark.component
def test_shootout_table_only_shown_when_match_had_one(patched_app):
    at = patched_app
    assert not any("Penalty shootout" in m.value for m in at.markdown)

    shootout = pd.DataFrame([
        {"team": "Home Team", "kick": 1, "player": "Player A", "scored": True},
        {"team": "Away Team", "kick": 1, "player": "Player X", "scored": False},
    ])
    # Nested patch overrides the fixture's empty shootout for this rerun only.
    with patch("data_loader.get_shootout", return_value=shootout):
        at.run()
    assert not at.exception
    assert any("Penalty shootout" in m.value for m in at.markdown)
    assert any('title="Player X"' in m.value for m in at.markdown)
