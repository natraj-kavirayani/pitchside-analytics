"""
Shared setup for the e2e suite.

Every e2e test needs a Streamlit server already running locally
(streamlit run app.py, default http://localhost:8501). Rather than each
test swallowing whatever exception page.goto() happens to raise, this
fixture checks for a reachable server up front with a plain socket
connection and skips with a clear reason when there isn't one. Skipped is
not the same as passed: pytest reports these distinctly, so a missing
server never looks like the app was verified working.
"""

import socket

import pytest

STREAMLIT_HOST = "localhost"
STREAMLIT_PORT = 8501


def _server_is_up() -> bool:
    try:
        with socket.create_connection((STREAMLIT_HOST, STREAMLIT_PORT), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(autouse=True)
def skip_if_no_local_streamlit_server():
    if not _server_is_up():
        pytest.skip(
            f"No Streamlit server reachable at http://{STREAMLIT_HOST}:{STREAMLIT_PORT} - "
            "start one with 'streamlit run app.py' before running the e2e suite."
        )
