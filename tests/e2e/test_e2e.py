"""
End-to-end browser tests against a locally running Streamlit server.

Run with: pytest -m e2e
Requires: streamlit run app.py (running on http://localhost:8501)
"""

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


@pytest.fixture
def loaded_page(page: Page) -> Page:
    page.goto(BASE_URL, timeout=15000)
    expect(page.locator("h1")).to_contain_text("Pitchside Analytics", timeout=15000)
    return page


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
