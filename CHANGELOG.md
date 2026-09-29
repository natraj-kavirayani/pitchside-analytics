# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
