"""
User journeys in a real browser, on live StatsBomb open data.

Run with: pytest -m e2e
Requires: streamlit run app.py (running on http://localhost:8501)

A user picks a specific match through the sidebar and checks what they
would actually look at. These use live data (the 2022 World Cup final),
so they also catch upstream data or API changes that the offline layers
cannot see.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.pages import open_app, open_tab, select_match

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
def final_page(page: Page, live_url: str) -> Page:
    """The app with the 2022 World Cup final selected through the sidebar."""
    open_app(page, live_url)
    # Live data is fetched after the last selection, so allow extra time.
    select_match(page, FINAL, timeout=90000)
    return page


@pytest.mark.e2e
def test_user_can_select_a_match_and_see_its_shot_map(final_page: Page):
    shot_panel = final_page.get_by_role("tabpanel", name="Shot map")
    expect(shot_panel.get_by_role("img")).to_be_visible(timeout=60000)
    expect(shot_panel.get_by_text("Bubble size = expected goals (xG)")).to_be_visible()


@pytest.mark.e2e
def test_summary_strip_leaves_shootout_kicks_out_of_xg(final_page: Page):
    """Counting the shootout's ten kicks at ~0.78 xG each pushed both
    teams past 5 xG. Real match xG for the final is around 2-3 each."""
    strip = final_page.get_by_role("group", name="Match summary")
    expect(strip).to_contain_text("Argentina")
    expect(strip).to_contain_text("France")
    xg_row = strip.locator(".ps-stat").first
    expect(xg_row).to_contain_text("xG")
    values = [float(v) for v in re.findall(r"\d+\.\d\d", xg_row.inner_text())]
    assert len(values) == 2 and all(0 < v < 5 for v in values), values


@pytest.mark.e2e
def test_shootout_match_shows_penalty_table_on_xg_timeline(final_page: Page):
    xg_panel = open_tab(final_page, "xG timeline")
    expect(xg_panel.get_by_role("heading", name="Penalty shootout")).to_be_visible(timeout=60000)
    expect(xg_panel.get_by_role("table")).to_contain_text("Argentina")
    expect(xg_panel.get_by_role("table")).to_contain_text("France")


@pytest.mark.e2e
def test_match_details_show_both_managers_and_starting_xis(final_page: Page):
    details = open_tab(final_page, "Match details")
    expect(details.get_by_text(re.compile(r"Manager: .*Scaloni"))).to_be_visible(timeout=60000)
    expect(details.get_by_text(re.compile(r"Manager: .*Deschamps"))).to_be_visible()
    # One starting-XI table per team, then substitution tables below.
    expect(details.get_by_test_id("stDataFrame").first).to_be_visible()
    expect(details.get_by_text("Starting XI not available")).to_have_count(0)
