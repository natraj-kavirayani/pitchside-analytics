# Testing strategy

This document explains what the tests are for, not just how to run them
(see the README for commands).

## What matters for this app

Pitchside Analytics shows numbers people draw conclusions from (xG, shot
counts, pass networks), on top of a third-party data source I don't
control. So the main quality risks are:

| Risk | Example | Where it is caught |
| --- | --- | --- |
| Wrong numbers that still look plausible | Penalty-shootout kicks counted as shots, inflating xG to 5-8+ per team in drawn knockout matches | Unit tests on the data functions (`tests/unit/test_data_loader.py`) |
| Edge cases in the data | Missing manager shown as "nan", a team with no shots, matches with no substitutions | Unit tests with hand-built data for each case |
| A screen breaks when wired together | A tab throws an exception, a chart or table never renders, a season with no matches | Component tests of the whole app via Streamlit's `AppTest` |
| The real app doesn't work for a user | Dropdowns, tabs or rendering fail in a browser | Playwright e2e tests |
| Upstream data or API changes | StatsBomb changes a field name or a match's data | E2E user journeys on live data (the mocked layers cannot see this) |
| Environment drift | Tests pass on one machine with different library versions | `requirements.lock` generated from the tested environment, used in CI |

## Why three layers

- **Unit tests** (fast, mocked, no network) cover the logic that produces
  numbers. This is where correctness bugs live and where they are
  cheapest to pin down, so it is the largest layer and has 100% line
  coverage of `data_loader.py`, `visualizations.py` and `styling.py`.
- **Component tests** run the whole Streamlit script headlessly with all
  data mocked. They check that every tab renders, without the cost and
  flakiness of a browser.
- **E2E tests** (Playwright) check what a user actually sees: smoke tests
  that every tab works, and user journeys through one fixed, well-known
  match (the 2022 World Cup final, which also went to penalties). They are
  the slowest layer and the only one using live data, so they are kept
  few and focused.

The fast layers run first in CI; the e2e job only runs once they pass. In
CI a missing app server fails the e2e job instead of skipping it, so the
pipeline can never be green without the browser tests having run.

The e2e tests wait for Streamlit's own "script finished" signal instead of
fixed sleeps, because every widget change re-runs the app and interacting
mid-rerun is a race.

## Deliberately not tested

- **Whether charts look right pixel by pixel.** Tests check that the right
  figure is built from the right data, not the rendered image. Visual
  regression testing would cost more than it is worth at this stage.
- **Every competition and match in StatsBomb's data.** The unit tests cover
  the edge cases; the e2e journeys use one representative match.
- **Browsers other than Chromium, performance and load.** This is a
  single-user hobby app; these would matter for a public deployment.

## Known gaps and next steps

- `app.py` is exercised by the component and e2e tests but is not part of
  the coverage measurement.
- A small "data contract" test that checks the StatsBomb fields the app
  relies on would catch upstream changes faster and more precisely than
  the e2e journeys do.
- If the app is deployed, the next step is production monitoring: an
  uptime check on Streamlit's `/_stcore/health` endpoint and logging of
  failed StatsBomb requests.

## How AI was used

The app and the test suite were built with an AI coding assistant
(Claude). Defects such as the penalty-shootout xG bug were found by
running the test suite locally; the assistant was then asked to fix them.
The e2e user journeys and the e2e CI job were added the same way.
