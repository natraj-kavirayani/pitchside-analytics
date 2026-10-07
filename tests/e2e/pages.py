"""Page helpers shared by the e2e tests: acting the way a user would."""

from playwright.sync_api import Locator, Page, expect

from pitchside.data.sample import COMPETITION_ID, MATCHES, SEASON_ID, SampleMatch, SampleSource
from pitchside.service import MatchService

# The sample server's data, for computing what the page should show.
SAMPLE = MatchService(SampleSource())
SHOOTOUT_MATCH = next(m for m in MATCHES if m.shootout)
NO_MANAGER_MATCH = next(m for m in MATCHES if m.away_manager is None)


def sidebar_for(match: SampleMatch) -> dict[str, str]:
    """The sidebar choices that select one sample match."""
    ref = next(r for r in SAMPLE.matches(COMPETITION_ID, SEASON_ID) if r.match_id == match.match_id)
    return {"Country": "Pitchside", "Competition": "Sample League", "Season": "Demo",
            "Match (optional)": ref.label}


def open_app(page: Page, url: str) -> Page:
    page.goto(url, timeout=15000)
    expect(page.locator("h1")).to_contain_text("Pitchside Analytics", timeout=15000)
    wait_until_idle(page)
    return page


def wait_until_idle(page: Page, timeout: float = 60000) -> None:
    """Wait for Streamlit to finish re-running the script.

    Every widget change (and, with lazy tabs, every tab click) re-runs
    the app. Interacting while that is still in progress is a race (a
    dropdown can be replaced mid-typing), so wait for the app's own "not
    running" signal rather than sleeping for a guessed amount of time.
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


def select_match(page: Page, selection: dict[str, str], timeout: float = 60000) -> None:
    """Fill in the sidebar fields in order and wait for the match to load."""
    for field, option in selection.items():
        choose(page, field, option)
    wait_until_idle(page, timeout=timeout)
    expect(page.get_by_role("heading", name=selection["Match (optional)"])).to_be_visible()


def open_tab(page: Page, label: str, timeout: float = 60000) -> Locator:
    """Click a tab, wait for its (lazily rendered) content, return its panel."""
    tab = page.get_by_role("tab", name=label)
    tab.click()
    expect(tab).to_have_attribute("aria-selected", "true")
    wait_until_idle(page, timeout=timeout)
    return page.get_by_role("tabpanel", name=label)
