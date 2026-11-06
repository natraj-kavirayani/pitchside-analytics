# Security policy

## Supported versions

Pitchside Analytics is maintained by one person and has no release
branches. Security fixes go into `main` only and are not backported.

| Version | Supported |
| ------- | --------- |
| Latest `main` (0.10.x) | :white_check_mark: |
| Anything older | :x: |

## Reporting a vulnerability

Please do not report security issues in public GitHub issues, pull
requests or discussions.

Report them privately through GitHub instead:
[**Report a vulnerability**](https://github.com/natraj-kavirayani/pitchside-analytics/security/advisories/new)
(also under the repository's **Security** tab). Only the maintainer can
see the report.

Please include:

- what the problem is and what an attacker could do with it
- steps to reproduce it, or a proof of concept
- the commit or version you tested against

What to expect:

- **Acknowledgement** within 7 days.
- **An assessment** (accepted or declined, with the reasoning) within
  14 days of the report.
- **If accepted**: a fix on `main`, then a published GitHub security
  advisory that credits you, unless you'd rather not be named. Please
  keep the issue private until the advisory is published.
- **If declined**: an explanation, for example that the issue is out of
  scope (see below) or belongs to a dependency.

## What the app does, from a security point of view

- It is a read-only viewer of public football data. It has no user
  accounts, logins, file uploads or database, and stores nothing a
  viewer enters. The only inputs are dropdowns, buttons, tabs and a
  toggle.
- It fetches StatsBomb's free open data over HTTPS from
  `raw.githubusercontent.com` (through `statsbombpy`), which needs no
  credentials. With `PITCHSIDE_DATA_SOURCE=sample` it uses a built-in
  sample league and makes no network requests for data.
- It renders some of its own HTML and CSS with Streamlit's
  `st.markdown(..., unsafe_allow_html=True)`. Every value from the data
  that goes into that HTML (team and player names) is escaped with
  `html.escape` first.

## Scope

In scope:

- Code in this repository, including HTML or script injection through
  data values the app renders.
- The GitHub Actions workflow in `.github/`.
- A dependency version pinned in `requirements.lock` that has a known
  vulnerability affecting how this app uses it.

Out of scope (please report these to the project concerned):

- Vulnerabilities in Streamlit, statsbombpy, mplsoccer, pandas,
  matplotlib or other dependencies themselves.
- The content of StatsBomb's open data
  ([statsbomb/open-data](https://github.com/statsbomb/open-data)).
- Streamlit Community Cloud or any other hosting platform.
- Denial of service through heavy traffic to a deployed copy of the app.

## If you deploy it yourself

Do not set `SB_USERNAME` and `SB_PASSWORD` in the app's environment.
`statsbombpy` reads them automatically and, when both are set, fetches
from StatsBomb's paid API with that account instead of the open data, so
everyone using your deployment would be using your StatsBomb account.
The app needs no credentials or secrets of any kind.
