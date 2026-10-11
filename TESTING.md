# Testing strategy

This document explains what the tests are for, not just how to run them
(see the README for commands).

## What matters for this app

Pitchside Analytics shows numbers people draw conclusions from (xG, shot
counts, pass networks), on top of a third-party data source I don't
control, through a UI styled by CSS that targets Streamlit's internal
markup. So the main quality risks are:

| Risk | Example | Where it is caught |
| --- | --- | --- |
| Wrong numbers that still look plausible | Penalty-shootout kicks counted as shots, inflating xG to 5-8+ per team in drawn knockout matches | Unit tests on the analytics (`tests/unit/analytics/`), plus property tests that hold for any match |
| Layers disagreeing | The summary strip and the xG timeline counting different shots | Integration tests (`tests/integration/`) |
| Edge cases in the data | Missing manager shown as "nan", a team with no shots, matches with no substitutions | Unit tests with hand-built data for each case |
| Upstream data or API changes | StatsBomb renames a field or starts writing "Complete" for completed passes | Contract tests against live data (`pytest -m live`), and the e2e journeys |
| Test data drifting from reality | The offline sample gains a shape the real data never has, so tests pass on fiction | The same contract tests, run against the sample in every test run |
| A screen breaks when wired together | A tab throws an exception, a chart or table never renders, a season with no matches | Component tests of the whole page via Streamlit's `AppTest` |
| Styling silently stops applying | Streamlit replaced its tab component and the colour-coded tabs quietly stopped working | E2E motion tests that read computed styles in a real browser |
| Motion that hurts more than helps | Content left invisible by an animation, slow transitions, motion for users who asked for none | Unit tests on the motion rules, e2e tests on what the browser actually plays |
| The real app doesn't work for a user | Dropdowns, tabs or rendering fail in a browser | Playwright e2e tests |
| Environment drift | Tests pass on one machine with different library versions | `requirements.lock` generated from the tested environment, used in CI |

## The layers

The code is layered (data source, analytics, service, UI; see the README),
and the tests follow the same seams. Each layer is tested through the
narrowest interface that can show its bugs:

- **Unit tests** (`unit`, fast, no I/O). The analytics are pure functions,
  so tests pass frames straight in with no mocking at all. Charts, tables,
  theme and motion rules are checked as data. The only mock left in the
  suite is `statsbombpy` itself, in the one test file for the class that
  calls it.
- **Property-based tests** (part of `unit`, with Hypothesis). Example
  tests only check the cases I thought of. These generate hundreds of
  random matches and check rules that must always hold: cumulative xG
  never decreases and ends at the sum of the shots, shootout kicks are
  never match shots, on-target never exceeds shots, no function modifies
  the frame it was given (sources share cached frames between callers).
- **Integration tests** (`integration`). `MatchService` wired to real
  sources: the layers agree with each other (summary, xG timeline and
  shot map count the same shots; goals match the scoreline), and caching
  works through the whole stack, not just in isolation.
- **Contract tests** (`contract`, plus `live` for the network half). One
  set of checks against `pitchside/data/schema.py`, run on both the
  offline sample league and StatsBomb's live data. Beyond column names,
  they pin down the value-level assumptions the analytics rely on.
- **Component tests** (`component`). The whole page runs headlessly with
  an in-memory service injected as an argument. Tabs are lazy, so each
  test selects a tab and checks that it rendered and that the others did
  not.
- **E2E tests** (`e2e`, Playwright). Smoke and motion tests run against
  the offline sample league, so they see the same data on every run and
  can compute the expected numbers with the same service the app uses.
  User journeys run through the 2022 World Cup final on live data. They
  are the slowest layer, so they are kept few and focused.

Plain `pytest` runs everything that needs neither a network nor a
server. In CI, the e2e job (both servers, plus the live contract tests)
only runs once the offline layers pass, and a missing server fails the
job instead of skipping it, so the pipeline can never be green without
the browser tests having run.

The e2e tests wait for Streamlit's own "script finished" signal instead
of fixed sleeps, because every widget change (and every tab click, with
lazy tabs) re-runs the app and interacting mid-rerun is a race.

## Testing motion

Animations are tested at two levels, for different reasons:

- **As rules** (`tests/unit/ui/test_motion.py`). Motion is declared as
  data, so tests can check things a reviewer would otherwise eyeball:
  every animation uses keyframes that exist, everything settles within
  1.2 seconds, every keyframe ends fully visible and in place, and all of
  it sits behind `prefers-reduced-motion: no-preference`.
- **In a browser** (`tests/e2e/test_motion.py`). Only a browser knows
  whether the selectors still match Streamlit's DOM and the animations
  actually play. These tests read the browser's own answers (computed
  styles and `element.getAnimations()`): a tab switch mounts a new panel
  that animates in, blocks enter in order, everything settles fully
  visible, each tab's indicator is in its accent colour, the summary bars
  end at the right proportions, and both the OS reduced-motion setting
  and the in-app toggle switch it all off. The match overview's shrink
  is recorded frame by frame: it must pass through several in-between
  sizes, the tabs must move up by exactly as much as the box shrinks in
  every frame (so it all happens at once), and the box must end exactly
  on the pill. They check outcomes, never
  pixels or frame timing, so a slow machine can't make them flake.

## What the deeper tests caught

Building the layered suite found real problems, which is the argument for
having it:

- **The colour-coded tabs had silently stopped working.** Streamlit 1.64
  replaced its tab component, and the CSS still targeted the old markup.
  The old suite checked that the CSS text contained seven colour rules,
  which stayed true. The new e2e test checks the computed colour.
- **Toggling a setting rebuilt the tab bar.** Removing the motion
  stylesheet shifted every element after it, and Streamlit identifies
  elements by position, so the tabs were briefly duplicated and the open
  tab was lost. Found by the e2e toggle test; the page now keeps the same
  elements either way, and a component test pins that down.
- **Lazy tabs leave empty placeholder panels**, which the panel animation
  was also being applied to. Found by the e2e motion tests.
- **Picking the match already on screen kept the overview collapsed.**
  When the dropdown choice was the current random match, the match didn't
  change, so the overview treated it as no selection. Found by an e2e
  test; the rule now reacts to any sidebar choice, and is a pure function
  with its own unit tests.
- **The match overview waited for the chart.** The overview was drawn
  after the open tab's chart, so its animation only started once the
  chart was rebuilt. Found by recording the shrink frame by frame; it is
  now drawn first.
- **Float rounding** made a bar share 100.00000000000001%. Found by a
  property test on the first run.
- **The sample league reused player names across teams**, so one team's
  substitute appeared in the other team's events. Found by the sample
  consistency tests.

Two limitations found the other way round, where `AppTest` behaves
differently from a browser:

- It doesn't send the open tab back on reruns, so after a widget change
  it falls back to the first tab. The component test works around it, and
  an e2e test (`test_widget_inside_a_tab_keeps_that_tab_open`) checks the
  real behaviour.
- After a button switches page (e.g. to About), its next rerun goes back
  to the default page. The component tests only check what the About page
  draws; using its controls is checked in the browser
  (`test_reduce_motion_on_the_about_page_stays_there`).

Moving About to its own page also needed a fix the browser tests check:
Streamlit forgets a widget's value while another page is open, so without
it the sidebar reset to the first match after visiting About.

## Deliberately not tested

- **Whether charts and animations look right pixel by pixel.** Tests
  check that the right figure is built from the right data, and that
  animations run and end in the right state, not the rendered image.
  Visual regression testing would cost more than it is worth at this
  stage.
- **Every competition and match in StatsBomb's data.** The unit and
  property tests cover the edge cases; the live checks use one
  representative match.
- **Browsers other than Chromium, performance and load.** This is a
  single-user hobby app; these would matter for a public deployment.
- **Hover effects.** They only change shadows and small offsets, and the
  transitions behind them are covered by the motion rules.

## Known gaps and next steps

- The live checks use one match. Sampling a few matches from different
  competitions would catch competition-specific data differences.
- If the app is deployed, the next step is production monitoring: an
  uptime check on Streamlit's `/_stcore/health` endpoint and logging of
  failed StatsBomb requests.

## How AI was used

The app and the test suite were built with an AI coding assistant
(Claude). Defects such as the penalty-shootout xG bug were found by
running the test suite locally; the assistant was then asked to fix them.
The e2e user journeys and the e2e CI job were added the same way.
