"""
Motion tests in a real browser, against the sample server.

Run with: pytest -m e2e
Requires: PITCHSIDE_DATA_SOURCE=sample streamlit run app.py --server.port 8502

The unit tests check the motion rules as text. Only a browser can tell
whether the selectors still match Streamlit's DOM and the animations
actually play, so these tests read the browser's own answers: computed
styles and the Web Animations API (``element.getAnimations()``). They
check outcomes (an animation ran, content ended fully visible, it
finished in time), never pixels or exact frame timing, so they don't
flake on a slow machine.
"""

import pytest
from playwright.sync_api import Page, expect

from pitchside.data.sample import MATCHES
from pitchside.ui.motion import MAX_SETTLE_MS
from pitchside.ui.views import VIEWS
from pitchside.viz.tables import SUMMARY_STATS, split_share
from tests.e2e.pages import SAMPLE, open_app, open_tab, select_match, sidebar_for, wait_until_idle

PANEL = "[data-testid=stTabPanel][role=tabpanel]"
# Generous slack on top of the design budget: CI machines are slow, and
# this checks "settles", not exact timing.
SETTLE_TIMEOUT_MS = MAX_SETTLE_MS + 4000

OUR_ANIMATIONS = "document.getAnimations().filter(a => (a.animationName || '').startsWith('ps-'))"


def wait_for_motion_to_settle(page: Page) -> None:
    page.wait_for_function(
        f"() => {OUR_ANIMATIONS}.every(a => a.playState === 'finished')",
        timeout=SETTLE_TIMEOUT_MS,
    )


def panel_animation(page: Page) -> str:
    return page.locator(PANEL).evaluate("el => getComputedStyle(el).animationName")


def hex_to_rgb(color: str) -> str:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgb({r}, {g}, {b})"


@pytest.fixture
def sample_page(page: Page, sample_url: str) -> Page:
    return open_app(page, sample_url)


@pytest.fixture
def reduced_motion_page(page: Page, sample_url: str) -> Page:
    page.emulate_media(reduced_motion="reduce")
    return open_app(page, sample_url)


# --- Tab transitions -------------------------------------------------------------

@pytest.mark.e2e
def test_tab_switch_mounts_a_new_panel_that_animates_in(sample_page: Page):
    """The tab transition relies on Streamlit mounting a fresh panel per
    switch, so the CSS entrance animation replays. If a Streamlit upgrade
    started reusing the panel, the transition would silently stop."""
    sample_page.locator(PANEL).evaluate("el => { window.__previousPanel = el; }")
    # A finished animation leaves getAnimations() (fill mode "backwards"),
    # so listen for it finishing instead.
    sample_page.evaluate("""() => {
        window.__panelAnimations = [];
        document.addEventListener('animationend', e => {
            if (e.target.matches('[data-testid=stTabPanel][role=tabpanel]'))
                window.__panelAnimations.push(e.animationName);
        });
    }""")
    open_tab(sample_page, "xG timeline")
    assert sample_page.locator(PANEL).evaluate("el => el !== window.__previousPanel")
    assert panel_animation(sample_page) == "ps-panel-in"
    sample_page.wait_for_function("() => window.__panelAnimations.includes('ps-panel-in')",
                                  timeout=SETTLE_TIMEOUT_MS)


@pytest.mark.e2e
def test_panel_blocks_enter_one_after_another(sample_page: Page):
    panel = open_tab(sample_page, "Match details")
    delays = panel.locator("> [data-testid=stVerticalBlock] > *").evaluate_all(
        "els => els.slice(0, 4).map(e => parseFloat(getComputedStyle(e).animationDelay))"
    )
    assert len(delays) >= 2
    assert delays == sorted(delays) and len(set(delays)) == len(delays)


@pytest.mark.e2e
def test_motion_settles_with_everything_fully_visible(sample_page: Page):
    open_tab(sample_page, "Shot map")
    wait_for_motion_to_settle(sample_page)
    for selector in (PANEL, ".ps-summary", ".ps-stat", ".ps-title"):
        opacity = sample_page.locator(selector).first.evaluate("el => getComputedStyle(el).opacity")
        assert opacity == "1", f"{selector} ended at opacity {opacity}"


# --- Tab colours -------------------------------------------------------------------

@pytest.mark.e2e
@pytest.mark.parametrize("view", VIEWS, ids=lambda v: v.label)
def test_selected_tab_indicator_uses_the_view_accent(sample_page: Page, view):
    """Would have caught the colour-coded tabs silently breaking when
    Streamlit replaced its tab component."""
    open_tab(sample_page, view.label)
    indicator = sample_page.locator("[role=tab][aria-selected=true] .react-aria-SelectionIndicator")
    expect(indicator).to_have_css("background-color", hex_to_rgb(view.accent))


# --- Reduced motion ------------------------------------------------------------------

@pytest.mark.e2e
def test_os_reduced_motion_setting_turns_motion_off(reduced_motion_page: Page):
    panel = open_tab(reduced_motion_page, "Pass network")
    assert panel_animation(reduced_motion_page) == "none"
    assert reduced_motion_page.evaluate(f"() => {OUR_ANIMATIONS}.length") == 0
    expect(panel.get_by_role("img").first).to_be_visible()


@pytest.mark.e2e
def test_reduce_motion_toggle_turns_motion_off_and_back_on(sample_page: Page):
    open_tab(sample_page, "Match details")
    toggle = sample_page.get_by_test_id("stSidebar").get_by_text("Reduce motion")
    toggle.click()
    wait_until_idle(sample_page)
    # Switching motion off must not rebuild the page: still one tab bar,
    # still on the same tab.
    expect(sample_page.get_by_role("tablist")).to_have_count(1)
    expect(sample_page.get_by_role("tab", name="Match details")).to_have_attribute("aria-selected", "true")
    open_tab(sample_page, "Pass map")
    assert panel_animation(sample_page) == "none"
    assert sample_page.evaluate(f"() => {OUR_ANIMATIONS}.length") == 0

    toggle.click()
    wait_until_idle(sample_page)
    open_tab(sample_page, "Shot map")
    assert panel_animation(sample_page) == "ps-panel-in"


# --- Animated content ends in the right place ---------------------------------------------

@pytest.mark.e2e
def test_summary_bars_grow_to_their_share(sample_page: Page):
    match = MATCHES[0]
    select_match(sample_page, sidebar_for(match))
    wait_for_motion_to_settle(sample_page)

    summary = SAMPLE.summary(match.match_id)
    widths = sample_page.locator(".ps-stat").evaluate_all("""rows => rows.map(r => {
        const [left, right] = [r.querySelector('.ps-bar-left'), r.querySelector('.ps-bar-right')]
            .map(b => b.getBoundingClientRect().width);
        return [left, right];
    })""")
    assert len(widths) == len(SUMMARY_STATS)
    for (label, column, _), (left, right) in zip(SUMMARY_STATS, widths):
        expected = split_share(*summary[column].astype(float))
        assert 100 * left / (left + right) == pytest.approx(expected, abs=2), label


@pytest.mark.e2e
def test_logo_bars_finish_at_full_height(sample_page: Page):
    wait_for_motion_to_settle(sample_page)
    heights = sample_page.locator(".ps-logo-bar").evaluate_all(
        "bars => bars.map(b => b.getBoundingClientRect().height)"
    )
    # The bars are 24, 40 and 58 units tall in the logo's viewBox.
    assert heights[0] > 0
    assert [h / heights[0] for h in heights] == pytest.approx([1, 40 / 24, 58 / 24], rel=0.05)


# --- About page ----------------------------------------------------------------------

@pytest.mark.e2e
def test_about_sections_rise_in_and_settle(sample_page: Page):
    sample_page.get_by_test_id("stSidebar").get_by_role("button", name="About", exact=True).click()
    sample_page.wait_for_url("**/about")
    wait_until_idle(sample_page)
    sections = sample_page.locator(".st-key-ps-about > *")
    names = sections.evaluate_all("els => els.map(e => getComputedStyle(e).animationName)")
    assert len(names) >= 6 and set(names) == {"ps-rise"}
    wait_for_motion_to_settle(sample_page)
    assert sections.evaluate_all("els => els.every(e => getComputedStyle(e).opacity === '1')")


@pytest.mark.e2e
def test_text_buttons_have_no_pill_border(sample_page: Page):
    about = sample_page.get_by_test_id("stSidebar").get_by_role("button", name="About", exact=True)
    shuffle = sample_page.get_by_test_id("stSidebar").get_by_role("button", name="Shuffle random match")
    expect(about).not_to_have_css("border-top-color", "rgb(34, 197, 94)")
    expect(shuffle).to_have_css("border-top-color", "rgb(34, 197, 94)")


# --- Match overview ---------------------------------------------------------------------

# Records, on every animation frame for ``ms``, the overview's height, the
# strip's width and where the tab bar starts, so a test can see the shape
# of the motion and not just where it ends.
START_RECORDING = """ms => {
  window.__frames = null;
  const frames = [], t0 = performance.now();
  const tick = () => {
    const box = document.querySelector('.st-key-ps-overview').getBoundingClientRect();
    const strip = document.querySelector('.st-key-ps-overview .ps-summary').getBoundingClientRect();
    const tabs = document.querySelector('[role=tablist]').getBoundingClientRect();
    frames.push({box: box.height, strip: strip.width, tabs: tabs.top});
    if (performance.now() - t0 < ms) requestAnimationFrame(tick); else window.__frames = frames;
  };
  requestAnimationFrame(tick);
}"""


def record_frames(page: Page, action, ms: int = 2500) -> list[dict]:
    page.evaluate(START_RECORDING, ms)
    action()
    page.wait_for_function("() => window.__frames", timeout=ms + 5000)
    return page.evaluate("() => window.__frames")


def in_between(frames: list[dict]) -> list[dict]:
    """Frames where the overview was neither at its start nor its end size."""
    start, end = frames[0]["box"], frames[-1]["box"]
    return [f for f in frames if min(start, end) + 1 < f["box"] < max(start, end) - 1]


def minimize(page: Page) -> None:
    page.get_by_role("button", name="Minimize").click()


def reopen(page: Page) -> None:
    page.get_by_role("button", name="Match overview").click()


@pytest.mark.e2e
def test_minimize_shrinks_the_box_while_the_tabs_move_up(sample_page: Page):
    wait_for_motion_to_settle(sample_page)
    frames = record_frames(sample_page, lambda: minimize(sample_page))
    first, last = frames[0], frames[-1]
    assert last["box"] < first["box"] / 3 and last["strip"] < first["strip"] / 2

    moving = in_between(frames)
    assert len(moving) >= 3, "Expected a smooth change over several frames, not a jump."
    for f in moving:
        assert last["strip"] < f["strip"] < first["strip"], "The box narrows as it shrinks."
        # All at once: in every frame, the tabs have moved up by exactly
        # as much as the overview has shrunk.
        assert first["tabs"] - f["tabs"] == pytest.approx(first["box"] - f["box"], abs=2)


@pytest.mark.e2e
def test_the_box_ends_exactly_where_the_pill_is(sample_page: Page):
    minimize(sample_page)
    pill = sample_page.get_by_role("button", name="Match overview")
    expect(pill).to_be_visible()
    wait_for_motion_to_settle(sample_page)
    sample_page.wait_for_timeout(800)  # transitions aren't in getAnimations() once done
    strip_box = sample_page.locator(".st-key-ps-overview .ps-summary").bounding_box()
    pill_box = pill.bounding_box()
    assert strip_box and pill_box
    for side in ("x", "y", "width", "height"):
        assert strip_box[side] == pytest.approx(pill_box[side], abs=2), side


@pytest.mark.e2e
def test_the_pill_grows_back_while_the_tabs_move_down(sample_page: Page):
    minimize(sample_page)
    expect(sample_page.get_by_role("button", name="Match overview")).to_be_visible()
    sample_page.wait_for_timeout(800)
    frames = record_frames(sample_page, lambda: reopen(sample_page))
    first, last = frames[0], frames[-1]
    assert last["box"] > first["box"] * 3
    moving = in_between(frames)
    assert len(moving) >= 3
    for f in moving:
        assert f["tabs"] - first["tabs"] == pytest.approx(f["box"] - first["box"], abs=2)
    expect(sample_page.get_by_role("group", name="Match summary")).to_be_visible()


@pytest.mark.e2e
def test_reduced_motion_switches_the_overview_at_once(reduced_motion_page: Page):
    frames = record_frames(reduced_motion_page, lambda: minimize(reduced_motion_page))
    assert frames[-1]["box"] < frames[0]["box"] / 3
    assert in_between(frames) == [], "No in-between frames when motion is reduced."
