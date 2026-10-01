"""
End-to-end browser tests against a locally running Streamlit server.

Run with: pytest -m e2e
Requires: streamlit run app.py (running on http://localhost:8501)

Two kinds of test live here:

- Smoke tests: the app loads, the sidebar renders, and every tab can be
  selected. They work with whatever match the app picks at random.
- User-journey tests: a user picks a specific match through the sidebar
  and checks what they would actually look at. These use live StatsBomb
  open data (the 2022 World Cup final), so they also catch upstream data
  or API changes that the mocked unit and component tests cannot see.
"""

import re

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8501"

TAB_LABELS = [
    "Shot map",
    "xG timeline",
    "Pass map",
    "Pass network",
    "Touch heatmap",
    "Match details",
    "About",
]

# The 2022 World Cup final: a fixed, well-known match in StatsBomb's open
# data. It ended 3-3 and went to penalties, so it also exercises the
# penalty shootout table and the fix that keeps shootout kicks out of xG.
FINAL = {
    "Country": "International",
    "Competition": "FIFA World Cup",
    "Season": "2022",
    "Match (optional)": "Argentina 3 - 3 France (2022-12-18)",
}


@pytest.fixture
def loaded_page(page: Page) -> Page:
    page.goto(BASE_URL, timeout=15000)
    expect(page.locator("h1")).to_contain_text("Pitchside Analytics", timeout=15000)
    return page


def wait_until_idle(page: Page, timeout: float = 60000) -> None:
    """Wait for Streamlit to finish re-running the script.

    Every widget change re-runs app.py and re-draws the sidebar. Interacting
    while that is still in progress is a race (a dropdown can be replaced
    mid-typing), so wait for the app's own "not running" signal rather than
    sleeping for a guessed amount of time.
    """
    expect(page.get_by_test_id("stApp")).to_have_attribute(
        "data-test-script-state", "notRunning", timeout=timeout
    )


def choose(page: Page, field: str, option: str) -> None:
    """Pick an option from a sidebar dropdown the way a user would: open it,
    type to filter (long lists such as a season's matches only render the
    first options), then click the match."""
    wait_until_idle(page)
    dropdown = page.get_by_test_id("stSidebar").get_by_role("combobox", name=field)
    if dropdown.input_value() == option:
        return
    dropdown.click()
    dropdown.press_sequentially(option)
    page.get_by_role("option", name=option, exact=True).click()
    expect(
        page.get_by_test_id("stSidebar").get_by_role("combobox", name=field)
    ).to_have_value(option)


@pytest.fixture
def final_page(loaded_page: Page) -> Page:
    """The app with the 2022 World Cup final selected through the sidebar."""
    for field, option in FINAL.items():
        choose(loaded_page, field, option)
    # Live data is fetched after the last selection, so allow extra time.
    wait_until_idle(loaded_page, timeout=90000)
    expect(loaded_page.get_by_role("heading", name=FINAL["Match (optional)"])).to_be_visible()
    return loaded_page


# --- Smoke tests -----------------------------------------------------------


@pytest.mark.e2e
def test_app_title_renders(loaded_page: Page):
    expect(loaded_page.locator("h1")).to_contain_text("Pitchside Analytics")


@pytest.mark.e2e
def test_sidebar_match_selector_renders(loaded_page: Page):
    expect(loaded_page.get_by_text("Select a match")).to_be_visible()


@pytest.mark.e2e
@pytest.mark.parametrize("tab_label", TAB_LABELS)
def test_tab_can_be_selected(loaded_page: Page, tab_label: str):
    """Every tab must be clickable and become the selected tab - checked
    individually so a single broken tab fails its own test instead of being
    hidden inside one big pass/fail for the whole nav bar."""
    tab = loaded_page.get_by_role("tab", name=tab_label)
    expect(tab).to_be_visible()
    tab.click()
    expect(tab).to_have_attribute("aria-selected", "true")


# --- User-journey tests ----------------------------------------------------


@pytest.mark.e2e
def test_user_can_select_a_match_and_see_its_shot_map(final_page: Page):
    shot_panel = final_page.get_by_role("tabpanel", name="Shot map")
    expect(shot_panel.get_by_role("img")).to_be_visible(timeout=60000)
    expect(shot_panel.get_by_text("Bubble size = expected goals (xG)")).to_be_visible()


@pytest.mark.e2e
def test_shootout_match_shows_penalty_table_on_xg_timeline(final_page: Page):
    final_page.get_by_role("tab", name="xG timeline").click()
    xg_panel = final_page.get_by_role("tabpanel", name="xG timeline")
    expect(xg_panel.get_by_role("heading", name="Penalty shootout")).to_be_visible(timeout=60000)
    expect(xg_panel.get_by_role("table")).to_contain_text("Argentina")
    expect(xg_panel.get_by_role("table")).to_contain_text("France")


@pytest.mark.e2e
def test_match_details_show_both_managers_and_starting_xis(final_page: Page):
    final_page.get_by_role("tab", name="Match details").click()
    details = final_page.get_by_role("tabpanel", name="Match details")
    expect(details.get_by_text(re.compile(r"Manager: .*Scaloni"))).to_be_visible(timeout=60000)
    expect(details.get_by_text(re.compile(r"Manager: .*Deschamps"))).to_be_visible()
    # One starting-XI table per team, then substitution tables below.
    expect(details.get_by_test_id("stDataFrame").first).to_be_visible()
    expect(details.get_by_text("Starting XI not available")).to_have_count(0)
