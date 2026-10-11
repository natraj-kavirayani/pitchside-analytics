# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.9.0] - 2026-10-02

### Added

- Motion: tabs slide in when you switch between them and their content
  follows in turn; the header logo, title and summary bars animate in;
  buttons, dropdowns and charts respond on hover. All of it is off for
  viewers whose device is set to reduce motion, and a **Reduce motion**
  switch in the sidebar turns it off in the app.
- Match overview above the tabs: each team's xG, shots, shots on target,
  passes and pass completion, as split bars. It shows when a match is
  picked. Its Minimize button, or opening another tab, shrinks it into a
  pill-shaped "Match overview" button in one smooth motion, with the tabs
  and chart moving up into the freed space at the same time; the pill
  grows it back.
- Offline sample league (`PITCHSIDE_DATA_SOURCE=sample`): three made-up
  matches, including a penalty shootout and a missing manager, for running
  without network access and for deterministic browser tests.
- Sidebar shows where the data comes from.
- About is now a separate page (`/about`) instead of a tab, opened from a
  text button at the bottom of the sidebar. Going back returns to the same
  match and tab.
- Test layers: property-based tests (Hypothesis) of the analytics,
  integration tests of the service, data contract tests run against both
  the sample and live StatsBomb data (`pytest -m live`), and e2e tests
  that check the animations and tab colours in a real browser.

### Changed

- The code is now a layered `pitchside` package: data sources, pure
  analytics, a `MatchService`, charts, and the UI. `data_loader.py`,
  `visualizations.py` and `styling.py` are replaced by it, and `app.py`
  is a thin entry point.
- Tabs are lazy: only the open tab is computed, instead of every chart
  on every interaction.
- Tabs are defined in one registry (label, colour, renderer) that the tab
  bar, the theme and the tests all read.
- The page takes its data service as an argument, so component tests run
  it on in-memory data with nothing patched.
- Test coverage now includes the UI code.
- CI starts a second, sample-data server for the e2e job and also runs
  the live data contract tests there.

### Fixed

- The colour-coded tab underlines had stopped showing since Streamlit
  1.64 replaced its tab component.

## [0.8.0] - 2026-10-01

### Added

- E2E user-journey tests: select the 2022 World Cup final through the
  sidebar, then check the shot map, the penalty shootout table on the xG
  timeline, and both managers and starting XIs in Match details. They use
  live StatsBomb data, so they also catch upstream data changes.
- E2E job in GitHub Actions: runs after the unit and component tests,
  starts the app, waits for its health check, and uploads screenshots,
  Playwright traces and the app log when a test fails.
- TESTING.md: quality risks, why each test layer exists, what is
  deliberately not tested, and how AI was used.

### Changed

- E2E tests wait for Streamlit to finish re-running instead of acting
  mid-rerun, which made dropdown selection flaky.
- In CI (`E2E_REQUIRE_SERVER=1`), a missing app server fails the e2e
  tests instead of skipping them.

### Fixed

- Plain `pytest` still ran the e2e tests when a server was on port 8501,
  although 0.7.0 said otherwise; `pyproject.toml` now excludes them by
  default.
- README test badge pointed to the repository's old name.

## [0.7.0] - 2026-09-29

- Planned: season-level aggregate stats, export charts as PNG.

### Added

- Penalty shootout table below the xG timeline, for matches decided on
  penalties: a check or red circle per kick, with the taker's name on
  hover.
- GitHub Actions workflow that runs the test suite on every push and
  pull request.

### Fixed

- xG timeline and shot map counted penalty shootout kicks as shots,
  inflating drawn knockout matches to 5-8+ xG per team.
- Plain `pytest` also ran the e2e tests whenever a server was on port
  8501; they now run only with `-m e2e`.
- `requirements.lock` was hand-written and pinned older versions
  (e.g. pandas 2.2, Streamlit 1.38) than the ones the tests were run
  against; it is now generated from the tested environment.
- Charts were never closed after rendering, so memory grew with every
  interaction in a long session.

### Removed

- Unused `get_teams` and `get_matches_for_team` helpers in `data_loader`.

## [0.6.0] - 2026-09-29

### Added

- xG timeline tab: each team's cumulative expected goals over the match,
  with goals marked, to show whether the scoreline matched the chances.
- Test suite: unit tests for data loading and plotting, headless
  component tests of the full app, and Playwright browser tests. All
  StatsBomb data is mocked, so the suite runs offline.

### Changed

- Renamed the app to Pitchside Analytics.
- The app now always uses a dark theme, so text stays readable for
  viewers whose system is in light mode.

### Fixed

- Match details showed "nan" instead of "Not available" when a
  manager was missing from the data.

## [0.5.0] - 2026-09-28

### Added

- Custom visual theme: gradient background, logo, colour-coded tabs and
  pill-shaped controls.
- About tab.

### Fixed

- Sidebar collapse button showed raw text instead of an arrow icon.

## [0.4.0] - 2026-09-27

### Added

- Pass network tab: each player at their average position, sized by
  passes made, linked to the teammates they passed to most. Uses only
  passes before each team's first substitution.

## [0.3.0] - 2026-09-27

### Added

- Match details tab: starting XIs with positions, managers, and a
  substitution timeline for each team.

### Changed

- Views moved from a sidebar radio button into tabs.

## [0.2.0] - 2026-09-26

### Changed

- Sidebar selection flow is now Country -> Competition -> Season ->
  Match, with a "Random match" option and a Shuffle button.

## [0.1.0] - 2026-09-24

### Added

- First version: pick a competition, season and match from StatsBomb's
  open data and view a shot map, pass map and touch heatmap.
