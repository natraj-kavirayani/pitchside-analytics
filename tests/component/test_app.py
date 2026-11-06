"""
Headless component tests of the whole page via Streamlit's AppTest.

The page takes its ``MatchService`` as an argument (``pitchside.ui.app.run``),
so each test hands it a service over in-memory frames: no patching, and
no test reaches StatsBomb. Tabs are lazy (only the selected one renders),
so a test selects a tab by setting its session-state key, as a click
would, and can then check both that the tab rendered and that the others
did not.
"""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitchside.data.source import InMemorySource
from pitchside.service import DATA_SOURCE_ENV, MatchService
from pitchside.ui.app import ABOUT_BUTTON_KEY, BACK_BUTTON_KEY, VIEW_KEY
from pitchside.ui.overview import BUTTON_KEY as OVERVIEW_BUTTON_KEY
from pitchside.ui.overview import MINIMIZE_KEY as OVERVIEW_MINIMIZE_KEY
from pitchside.ui.sidebar import REDUCE_MOTION_KEY
from pitchside.ui.views import VIEWS

APP_PATH = str(Path(__file__).resolve().parents[2] / "app.py")
MATCH_LABEL = "Home Team 2 - 1 Away Team (2016-05-01)"


def _page(service):
    # AppTest runs this function's source as a standalone script, so the
    # import has to live inside it.
    from pitchside.ui.app import run
    run(service)


def app_for(service: MatchService) -> AppTest:
    return AppTest.from_function(_page, args=(service,), default_timeout=30)


def select_match(at: AppTest, label: str = MATCH_LABEL) -> AppTest:
    return at.sidebar.selectbox[3].select(label).run()


def open_view(at: AppTest, label: str) -> AppTest:
    at.session_state[VIEW_KEY] = label
    return at.run()


def markdown_text(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


def captions(at: AppTest) -> str:
    return "\n".join(c.value for c in at.caption)


def in_order(block) -> list:
    """Every element under ``block``, in the order they appear on screen."""
    nodes = []
    for child in block.children.values():
        nodes.append(child)
        nodes.extend(in_order(child) if hasattr(child, "children") else [])
    return nodes


def overview_shown(at: AppTest) -> bool:
    """True if the overview is open, False if shrunk to its pill.

    Both forms are always on the page (so the browser can animate between
    them); the state marker says which one shows.
    """
    markers = [m.value for m in at.markdown if m.value.startswith('<span class="ps-overview-state"')]
    assert len(markers) == 1
    return 'data-open="true"' in markers[0]


def open_about(at: AppTest) -> AppTest:
    return at.button(key=ABOUT_BUTTON_KEY).click().run()


class RecordingService(MatchService):
    """A real MatchService that also records pass-map queries."""

    def __init__(self, source) -> None:
        super().__init__(source, label="test frames")
        self.pass_queries: list[str | None] = []

    def passes(self, match_id, team=None, player=None):
        self.pass_queries.append(player)
        return super().passes(match_id, team=team, player=player)


@pytest.fixture
def at(frames_service) -> AppTest:
    return select_match(app_for(frames_service).run())


# What only each view puts on the page, to tell which one rendered.
VIEW_MARKERS = {
    "Shot map": lambda at: "Bubble size = expected goals" in captions(at),
    "xG timeline": lambda at: "Each step is a shot" in captions(at),
    "Pass map": lambda at: any(s.label == "Player (optional filter)" for s in at.main.selectbox),
    "Pass network": lambda at: "Node position" in captions(at),
    # AppTest models st.pyplot as an "image" element.
    "Touch heatmap": lambda at: len(at.get("image")) == 1 and not at.main.caption,
    "Match details": lambda at: "### Starting XI" in markdown_text(at),
}


# --- Page structure ------------------------------------------------------------

@pytest.mark.component
def test_page_loads_with_header_sidebar_and_data_label(at):
    assert not at.exception
    assert "Pitchside Analytics" in markdown_text(at)
    assert any("Select a match" in h.value for h in at.sidebar.header)
    assert any("Data: test frames" in c.value for c in at.sidebar.caption)


@pytest.mark.component
def test_one_tab_per_registered_view_in_order(at):
    assert [t.label for t in at.tabs] == [v.label for v in VIEWS]


@pytest.mark.component
def test_registry_markers_cover_every_view():
    assert set(VIEW_MARKERS) == {v.label for v in VIEWS}


@pytest.mark.component
def test_subheader_and_summary_strip_show_the_selected_match(at):
    assert [s.value for s in at.subheader] == [MATCH_LABEL]
    assert 'class="ps-summary"' in markdown_text(at)
    assert "Home Team" in markdown_text(at) and "Away Team" in markdown_text(at)


# --- Lazy tabs ------------------------------------------------------------------

@pytest.mark.component
@pytest.mark.parametrize("view", [v.label for v in VIEWS])
def test_selecting_a_tab_renders_only_that_view(at, view):
    at = open_view(at, view)
    assert not at.exception
    rendered = [label for label, marker in VIEW_MARKERS.items() if marker(at)]
    assert rendered == [view]


@pytest.mark.component
def test_first_tab_is_open_by_default(frames_service):
    at = select_match(app_for(frames_service).run())
    assert VIEW_MARKERS["Shot map"](at)
    assert not VIEW_MARKERS["xG timeline"](at)


# --- Motion ---------------------------------------------------------------------

@pytest.mark.component
def test_motion_and_theme_css_are_injected_by_default(at):
    css = markdown_text(at)
    assert "@keyframes ps-panel-in" in css
    assert all(v.accent in css for v in VIEWS), "Every tab's accent colour should be in the theme."


@pytest.mark.component
def test_reduce_motion_toggle_removes_all_motion_but_keeps_the_theme(at):
    at = at.toggle(key=REDUCE_MOTION_KEY).set_value(True).run()
    css = markdown_text(at)
    assert "@keyframes" not in css and "transition:" not in css
    assert "linear-gradient" in css, "The static theme must stay when motion is off."

    at = at.toggle(key=REDUCE_MOTION_KEY).set_value(False).run()
    assert "@keyframes ps-panel-in" in markdown_text(at)


@pytest.mark.component
def test_reduce_motion_keeps_the_same_elements_on_the_page(at):
    """Streamlit identifies elements by position: dropping the motion
    stylesheet would shift the tabs and rebuild them, losing the open tab."""
    before = len(at.markdown)
    at = at.toggle(key=REDUCE_MOTION_KEY).set_value(True).run()
    assert len(at.markdown) == before


@pytest.mark.component
def test_reduce_motion_survives_switching_tabs(at):
    at = at.toggle(key=REDUCE_MOTION_KEY).set_value(True).run()
    at = open_view(at, "Pass network")
    assert "@keyframes" not in markdown_text(at)


# --- Sidebar --------------------------------------------------------------------

@pytest.mark.component
def test_random_match_is_stable_across_tab_switches(frames_service):
    at = app_for(frames_service).run()
    picked = at.subheader[0].value
    for view in VIEWS:
        at = open_view(at, view.label)
        assert at.subheader[0].value == picked


@pytest.mark.component
def test_shuffle_button_rerolls_without_error(frames_service):
    at = app_for(frames_service).run()
    shuffle = [b for b in at.button if "Shuffle" in b.label]
    assert shuffle, "Expected a 'Shuffle random match' button while on Random match."
    at = shuffle[0].click().run()
    assert not at.exception
    assert at.subheader[0].value.startswith(("Home Team", "Away Team"))


@pytest.mark.component
def test_choosing_a_match_hides_the_shuffle_button(at):
    assert not [b for b in at.button if "Shuffle" in b.label]


@pytest.mark.component
def test_no_matches_stops_with_warning_but_keeps_settings(competitions_frame):
    service = MatchService(InMemorySource(competitions_frame, matches={}, events={}))
    at = app_for(service).run()
    assert any("No matches found" in w.value for w in at.warning)
    assert not at.tabs
    assert at.toggle(key=REDUCE_MOTION_KEY), "Display settings should render even when stopped."


# --- Match overview ---------------------------------------------------------------

@pytest.mark.component
def test_overview_is_shown_when_a_match_is_selected(at):
    assert overview_shown(at)


@pytest.mark.component
def test_overview_shrinks_to_a_button_once_another_tab_is_opened(at):
    at = open_view(at, "xG timeline")
    assert not overview_shown(at)
    button = at.button(key=OVERVIEW_BUTTON_KEY)
    assert button.label == "Match overview"
    assert VIEW_MARKERS["xG timeline"](at), "The tab itself still renders."


@pytest.mark.component
def test_minimize_button_shrinks_the_overview(at):
    at.button(key=OVERVIEW_MINIMIZE_KEY).click()
    at = open_view(at, "Shot map")  # AppTest doesn't re-send the open tab
    assert not overview_shown(at)
    assert VIEW_MARKERS["Shot map"](at)


@pytest.mark.component
def test_overview_draws_the_same_elements_open_or_closed(at):
    """The browser can only animate between the two forms if every element
    survives the rerun, so open and closed must draw the same elements."""
    def kinds(at):
        strip = [m for m in at.markdown if 'class="ps-summary"' in m.value]
        keys = [b.key for b in at.button if b.key in {OVERVIEW_BUTTON_KEY, OVERVIEW_MINIMIZE_KEY}]
        return len(strip), sorted(keys), len(at.markdown)

    opened = kinds(at)
    closed = kinds(open_view(at, "Pass map"))
    assert opened == closed == (1, sorted([OVERVIEW_BUTTON_KEY, OVERVIEW_MINIMIZE_KEY]), opened[2])


@pytest.mark.component
def test_overview_button_is_above_the_tabs(at):
    at = open_view(at, "Pass network")
    order = in_order(at.main)
    button = next(i for i, n in enumerate(order) if getattr(n, "key", None) == OVERVIEW_BUTTON_KEY)
    tabs = next(i for i, n in enumerate(order) if getattr(n, "type", None) == "tab")
    assert button < tabs


@pytest.mark.component
def test_overview_button_brings_the_strip_back_on_the_same_tab(at):
    at = open_view(at, "Match details")
    at.button(key=OVERVIEW_BUTTON_KEY).click()
    at = open_view(at, "Match details")  # AppTest doesn't re-send the open tab
    assert overview_shown(at)
    assert VIEW_MARKERS["Match details"](at)


@pytest.mark.component
def test_reopened_overview_shrinks_again_on_the_next_tab(at):
    at = open_view(at, "Match details")
    at.button(key=OVERVIEW_BUTTON_KEY).click()
    at = open_view(at, "Match details")
    at = open_view(at, "Shot map")
    assert not overview_shown(at)


@pytest.fixture
def both_matches_service(competitions_frame, matches_frame, events_frame) -> MatchService:
    """Like frames_service, but both matches have events, so either one
    (including a random pick) has an overview to show."""
    return MatchService(InMemorySource(
        competitions_frame, matches={(2, 44): matches_frame},
        events={12345: events_frame, 67890: events_frame},
    ))


@pytest.mark.component
def test_choosing_another_match_shows_its_overview(both_matches_service):
    at = open_view(select_match(app_for(both_matches_service).run()), "Pass map")
    assert not overview_shown(at)
    at = select_match(at, "Away Team 0 - 0 Third Team (2016-05-08)")
    at = open_view(at, "Pass map")
    assert overview_shown(at)


@pytest.mark.component
def test_naming_the_current_random_match_still_shows_its_overview(both_matches_service):
    """Found by the e2e suite: the match didn't change, so the overview
    used to stay collapsed although the viewer had just picked a match."""
    at = app_for(both_matches_service).run()
    random_label = at.subheader[0].value
    at = open_view(at, "Pass network")
    assert not overview_shown(at)
    at = open_view(select_match(at, random_label), "Pass network")
    assert overview_shown(at)


@pytest.mark.component
def test_collapsed_overview_stays_collapsed_after_visiting_about(at):
    at = open_view(at, "Pass network")
    at = open_about(at).button(key=BACK_BUTTON_KEY).click().run()
    at = open_view(at, "Pass network")
    assert not overview_shown(at)


# --- About page --------------------------------------------------------------------

@pytest.mark.component
def test_about_is_a_text_button_at_the_bottom_of_the_sidebar(at):
    button = at.button(key=ABOUT_BUTTON_KEY)
    assert button.label == "About" and button.proto.type == "tertiary"
    widgets = [n for n in in_order(at.sidebar) if getattr(n, "type", None) in {"button", "toggle", "selectbox"}]
    assert widgets[-1].key == ABOUT_BUTTON_KEY


@pytest.mark.component
def test_about_opens_a_page_of_its_own(at):
    at = open_about(at)
    assert not at.exception
    assert "### About Pitchside Analytics" in markdown_text(at)
    assert "Pitchside Analytics" in markdown_text(at), "The header stays."
    assert not at.tabs and not at.subheader, "No match tabs or match on the About page."
    assert not at.sidebar.selectbox, "No match picker on the About page."
    back = at.button(key=BACK_BUTTON_KEY)
    assert back.label == "← Back to matches" and back.proto.type == "tertiary"


@pytest.mark.component
def test_about_page_keeps_the_display_settings(at):
    # Only checks the toggle is drawn: after an in-script page switch,
    # AppTest's next rerun goes back to the default page, which a browser
    # doesn't. Using it on the About page is covered in
    # tests/e2e/test_smoke.py (test_reduce_motion_on_the_about_page_stays_there).
    at = open_about(at)
    assert at.toggle(key=REDUCE_MOTION_KEY)
    assert any("Data: test frames" in c.value for c in at.sidebar.caption)


@pytest.mark.component
def test_back_returns_to_the_same_match_and_tab(at):
    at = open_view(at, "Match details")
    at = open_about(at)
    at = at.button(key=BACK_BUTTON_KEY).click().run()
    assert not at.exception
    assert [s.value for s in at.subheader] == [MATCH_LABEL]
    assert at.sidebar.selectbox[3].value == MATCH_LABEL
    assert VIEW_MARKERS["Match details"](at)


@pytest.mark.component
def test_back_keeps_a_random_pick(frames_service):
    at = app_for(frames_service).run()
    picked = at.subheader[0].value
    at = open_about(at).button(key=BACK_BUTTON_KEY).click().run()
    assert at.subheader[0].value == picked


@pytest.mark.component
def test_about_link_shown_even_when_a_season_has_no_matches(competitions_frame):
    service = MatchService(InMemorySource(competitions_frame, matches={}, events={}))
    at = app_for(service).run()
    assert any("No matches found" in w.value for w in at.warning)
    at = open_about(at)
    assert "### About Pitchside Analytics" in markdown_text(at)


# --- Views in detail ---------------------------------------------------------------

@pytest.mark.component
def test_pass_map_player_filter_queries_that_player(frames_source):
    service = RecordingService(frames_source)
    at = open_view(select_match(app_for(service).run()), "Pass map")
    assert service.pass_queries[-1] is None, "Defaults to all players."

    # A browser sends the open tab back with every rerun; AppTest models
    # tabs as plain blocks and doesn't, so re-send it here. The real
    # behaviour is pinned by test_widget_inside_a_tab_keeps_that_tab_open
    # in tests/e2e/test_smoke.py.
    at.main.selectbox[0].select("Player B")
    at = open_view(at, "Pass map")
    assert not at.exception
    assert service.pass_queries[-1] == "Player B"


@pytest.mark.component
def test_shootout_table_only_shown_when_match_had_one(
    competitions_frame, matches_frame, events_frame, shootout_events,
):
    with_shootout = pd.concat([events_frame, shootout_events], ignore_index=True)
    service = MatchService(InMemorySource(
        competitions_frame, matches={(2, 44): matches_frame},
        events={12345: with_shootout, 67890: events_frame},
    ))
    at = open_view(select_match(app_for(service).run()), "xG timeline")
    assert "Penalty shootout" in markdown_text(at)
    assert 'title="Player Y"' in markdown_text(at)

    at = open_view(select_match(at, "Away Team 0 - 0 Third Team (2016-05-08)"), "xG timeline")
    assert "Penalty shootout" not in markdown_text(at)


@pytest.mark.component
def test_match_details_show_managers_lineups_and_substitutions(at):
    at = open_view(at, "Match details")
    assert {"Manager: Home Manager", "Manager: Away Manager"} <= {c.value for c in at.caption}
    # Two starting-XI tables, then one substitution table (Home only).
    assert len(at.dataframe) == 3
    assert any("No substitutions for this team." in m.value for m in at.markdown)


@pytest.mark.component
def test_match_details_show_unknown_shirt_numbers_as_not_available(
    competitions_frame, matches_frame, events_frame, lineups_dict,
):
    lineups = {team: df.copy() for team, df in lineups_dict.items()}
    lineups["Away Team"]["jersey_number"] = 0  # StatsBomb's "unknown"
    service = MatchService(InMemorySource(
        competitions_frame, matches={(2, 44): matches_frame},
        events={12345: events_frame}, lineups={12345: lineups},
    ))
    at = open_view(select_match(app_for(service).run()), "Match details")
    numbers = sorted(list(table.value["#"]) for table in at.dataframe[:2])
    assert numbers == [["9", "10"], ["N/A"]]


@pytest.mark.component
def test_match_details_without_lineups_says_so(competitions_frame, matches_frame, events_frame):
    service = MatchService(InMemorySource(
        competitions_frame, matches={(2, 44): matches_frame},
        events={12345: events_frame}, lineups={},
    ))
    at = open_view(select_match(app_for(service).run()), "Match details")
    assert not at.exception
    missing = [m for m in at.markdown if "Starting XI not available" in m.value]
    assert len(missing) == 2, "One message per team."


@pytest.mark.component
def test_match_details_without_substitutions_says_so(competitions_frame, matches_frame, events_frame):
    no_subs = events_frame[events_frame["type"] != "Substitution"]
    service = MatchService(InMemorySource(
        competitions_frame, matches={(2, 44): matches_frame}, events={12345: no_subs},
    ))
    at = open_view(select_match(app_for(service).run()), "Match details")
    assert any("No substitutions recorded for this match." in m.value for m in at.markdown)


# --- Entry point ---------------------------------------------------------------------

@pytest.mark.component
def test_app_py_runs_on_the_sample_league(monkeypatch):
    monkeypatch.setenv(DATA_SOURCE_ENV, "sample")
    at = AppTest.from_file(APP_PATH, default_timeout=60).run()
    assert not at.exception
    assert any("Data: offline sample league" in c.value for c in at.sidebar.caption)
    assert at.subheader and " - " in at.subheader[0].value
