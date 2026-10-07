"""
Smoke tests in a real browser, against the sample server.

Run with: pytest -m e2e
Requires: PITCHSIDE_DATA_SOURCE=sample streamlit run app.py --server.port 8502

The sample league is fixed, so these tests know exactly what the page
should show, and compute the expected numbers with the same
``MatchService`` the app uses: the browser has to show what the service
layer computed, end to end.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pitchside.ui.views import VIEWS
from tests.e2e.pages import (
    NO_MANAGER_MATCH,
    SAMPLE,
    SHOOTOUT_MATCH,
    open_app,
    open_tab,
    select_match,
    sidebar_for,
    wait_until_idle,
)

@pytest.fixture
def sample_page(page: Page, sample_url: str) -> Page:
    return open_app(page, sample_url)


@pytest.mark.e2e
def test_sidebar_shows_the_sample_data_source(sample_page: Page):
    sidebar = sample_page.get_by_test_id("stSidebar")
    expect(sidebar.get_by_text("Select a match")).to_be_visible()
    expect(sidebar.get_by_text("Data: offline sample league")).to_be_visible()


@pytest.mark.e2e
@pytest.mark.parametrize("label", [v.label for v in VIEWS])
def test_every_tab_opens_with_content(sample_page: Page, label: str):
    """Checked one tab per test, so a single broken tab fails on its own."""
    panel = open_tab(sample_page, label)
    expect(panel).to_be_visible()
    expect(panel.locator("[data-testid=stElementContainer]").first).to_be_visible()
    expect(sample_page.get_by_test_id("stException")).to_have_count(0)


@pytest.mark.e2e
def test_summary_strip_shows_what_the_service_computed(sample_page: Page):
    select_match(sample_page, sidebar_for(SHOOTOUT_MATCH))
    summary = SAMPLE.summary(SHOOTOUT_MATCH.match_id)
    strip = sample_page.get_by_role("group", name="Match summary")
    for _, row in summary.iterrows():
        expect(strip).to_contain_text(row["team"])
        expect(strip).to_contain_text(f"{row['xg']:.2f}")
        expect(strip).to_contain_text(f"{row['pass_completion']:.0f}%")


@pytest.mark.e2e
def test_shootout_match_shows_every_kick(sample_page: Page):
    select_match(sample_page, sidebar_for(SHOOTOUT_MATCH))
    panel = open_tab(sample_page, "xG timeline")
    table = panel.get_by_role("table")
    expect(table).to_contain_text(SHOOTOUT_MATCH.home_team)
    kicks = SAMPLE.shootout(SHOOTOUT_MATCH.match_id)
    expect(table.locator("td[title]")).to_have_count(len(kicks))


@pytest.mark.e2e
def test_missing_manager_reads_not_available(sample_page: Page):
    select_match(sample_page, sidebar_for(NO_MANAGER_MATCH))
    panel = open_tab(sample_page, "Match details")
    expect(panel.get_by_text(f"Manager: {NO_MANAGER_MATCH.home_manager}")).to_be_visible()
    expect(panel.get_by_text("Manager: Not available")).to_be_visible()
    expect(panel.get_by_text(re.compile(r"nan", re.IGNORECASE))).to_have_count(0)


@pytest.mark.e2e
def test_widget_inside_a_tab_keeps_that_tab_open(sample_page: Page):
    """Tabs are lazy and every widget change re-runs the page, so the open
    tab must survive the rerun (headless AppTest can't check this)."""
    select_match(sample_page, sidebar_for(SHOOTOUT_MATCH))
    panel = open_tab(sample_page, "Pass map")
    player = SAMPLE.passers(SHOOTOUT_MATCH.match_id)[0]
    dropdown = panel.get_by_role("combobox", name="Player (optional filter)")
    dropdown.click()
    dropdown.press_sequentially(player)
    sample_page.get_by_role("option", name=player, exact=True).click()
    wait_until_idle(sample_page)
    expect(sample_page.get_by_role("tab", name="Pass map")).to_have_attribute("aria-selected", "true")
    expect(panel.get_by_role("combobox", name="Player (optional filter)")).to_have_value(player)


@pytest.mark.e2e
def test_open_tab_survives_changing_the_match(sample_page: Page):
    open_tab(sample_page, "Match details")
    select_match(sample_page, sidebar_for(NO_MANAGER_MATCH))
    expect(sample_page.get_by_role("tab", name="Match details")).to_have_attribute("aria-selected", "true")


# --- About page ------------------------------------------------------------------


def open_about(page: Page) -> None:
    page.get_by_test_id("stSidebar").get_by_role("button", name="About", exact=True).click()
    page.wait_for_url("**/about")
    wait_until_idle(page)


@pytest.mark.e2e
def test_about_is_the_last_thing_in_the_sidebar(sample_page: Page):
    buttons = sample_page.get_by_test_id("stSidebar").get_by_role("button")
    expect(buttons.last).to_have_text("About")
    expect(buttons.last).to_have_attribute("kind", "tertiary")


@pytest.mark.e2e
def test_about_opens_its_own_page(sample_page: Page):
    open_about(sample_page)
    expect(sample_page).to_have_title("About · Pitchside Analytics")
    expect(sample_page.get_by_role("heading", name="About Pitchside Analytics")).to_be_visible()
    expect(sample_page.get_by_role("tablist")).to_have_count(0)
    expect(sample_page.get_by_test_id("stSidebar").get_by_role("combobox")).to_have_count(0)


@pytest.mark.e2e
def test_about_page_opens_from_its_url(page: Page, sample_url: str):
    page.goto(f"{sample_url}/about")
    expect(page.get_by_role("heading", name="About Pitchside Analytics")).to_be_visible(timeout=15000)
    expect(page.get_by_role("button", name="← Back to matches")).to_be_visible()


@pytest.mark.e2e
def test_back_returns_to_the_same_match_and_tab(sample_page: Page):
    selection = sidebar_for(NO_MANAGER_MATCH)
    select_match(sample_page, selection)
    open_tab(sample_page, "Match details")
    open_about(sample_page)

    sample_page.get_by_role("button", name="← Back to matches").click()
    wait_until_idle(sample_page)
    expect(sample_page.get_by_role("heading", name=selection["Match (optional)"])).to_be_visible()
    expect(sample_page.get_by_role("tab", name="Match details")).to_have_attribute("aria-selected", "true")
    sidebar = sample_page.get_by_test_id("stSidebar")
    for field, option in selection.items():
        expect(sidebar.get_by_role("combobox", name=field)).to_have_value(option)


@pytest.mark.e2e
def test_reduce_motion_on_the_about_page_stays_there(sample_page: Page):
    open_about(sample_page)
    sample_page.get_by_test_id("stSidebar").get_by_text("Reduce motion").click()
    wait_until_idle(sample_page)
    expect(sample_page).to_have_url(re.compile(r"/about$"))
    expect(sample_page.get_by_role("heading", name="About Pitchside Analytics")).to_be_visible()


# --- Match overview --------------------------------------------------------------


def overview_strip(page: Page):
    return page.get_by_role("group", name="Match summary")


def overview_button(page: Page):
    return page.get_by_role("button", name="Match overview")


@pytest.mark.e2e
def test_overview_shrinks_to_a_button_when_a_tab_is_clicked(sample_page: Page):
    expect(overview_strip(sample_page)).to_be_visible()
    expect(overview_button(sample_page)).to_have_count(0)

    open_tab(sample_page, "xG timeline")
    expect(overview_strip(sample_page)).to_have_count(0)
    expect(overview_button(sample_page)).to_be_visible()
    button_box = overview_button(sample_page).bounding_box()
    tabs_box = sample_page.get_by_role("tablist").bounding_box()
    assert button_box and tabs_box and button_box["y"] < tabs_box["y"], "The button sits above the tabs."


@pytest.mark.e2e
def test_overview_button_brings_the_strip_back(sample_page: Page):
    open_tab(sample_page, "Pass network")
    overview_button(sample_page).click()
    wait_until_idle(sample_page)
    expect(overview_strip(sample_page)).to_be_visible()
    expect(overview_button(sample_page)).to_have_count(0)
    expect(sample_page.get_by_role("tab", name="Pass network")).to_have_attribute("aria-selected", "true")

    open_tab(sample_page, "Match details")
    expect(overview_strip(sample_page)).to_have_count(0)


@pytest.mark.e2e
def test_selecting_another_match_shows_its_overview(sample_page: Page):
    open_tab(sample_page, "Touch heatmap")
    expect(overview_strip(sample_page)).to_have_count(0)
    select_match(sample_page, sidebar_for(SHOOTOUT_MATCH))
    expect(overview_strip(sample_page)).to_contain_text(SHOOTOUT_MATCH.home_team)
