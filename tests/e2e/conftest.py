"""
Shared setup for the e2e suite.

The e2e tests drive real browsers against two locally running servers:

- the sample server (``PITCHSIDE_DATA_SOURCE=sample``, port 8502): the
  offline sample league, so smoke and motion tests see the same data on
  every run;
- the live server (default data source, port 8501): StatsBomb's open
  data, for the user journeys through a real match.

Rather than each test swallowing whatever exception page.goto() happens
to raise, the server fixtures check for a reachable server up front with
a plain socket connection and skip with a clear reason when there isn't
one. Skipped is not the same as passed: pytest reports these distinctly,
so a missing server never looks like the app was verified working.

In CI a skip would still let the pipeline go green without a single
browser test having run, so CI sets E2E_REQUIRE_SERVER=1 and a missing
server becomes a hard failure instead.
"""

import os
import socket

import pytest

HOST = "localhost"
LIVE_PORT = 8501
SAMPLE_PORT = 8502


def _server_is_up(port: int) -> bool:
    try:
        with socket.create_connection((HOST, port), timeout=1):
            return True
    except OSError:
        return False


def _require_server(port: int, command: str) -> str:
    url = f"http://{HOST}:{port}"
    if _server_is_up(port):
        return url
    message = f"No Streamlit server reachable at {url} - start one with '{command}'."
    if os.environ.get("E2E_REQUIRE_SERVER") == "1":
        pytest.fail(message)
    pytest.skip(message)


@pytest.fixture
def sample_url() -> str:
    return _require_server(
        SAMPLE_PORT,
        f"PITCHSIDE_DATA_SOURCE=sample streamlit run app.py --server.port {SAMPLE_PORT}",
    )


@pytest.fixture
def live_url() -> str:
    return _require_server(LIVE_PORT, "streamlit run app.py")
