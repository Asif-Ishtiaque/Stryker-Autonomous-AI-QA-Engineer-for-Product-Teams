"""e2e test fixtures.

Serves tests/e2e/fixtures/demo_app.html over a real local HTTP server (so
WebExecutor's `urljoin(base_url, path)` navigation behaves exactly like it
would against a real application under test), and starts a real (small)
Playwright browser pool for the one test in this directory to drive.

Nothing here mocks Playwright, the self-healing locator engine, or evidence
capture — only the LLM provider is a stub (see tests/support/stubs.py),
per the task: those are the things this suite exists to prove work for real.
"""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "h2iPuG1_CJtLhpeDDvytAs9k0Gzc023YYVYEkeLEZ5U=")
os.environ.setdefault("ENABLE_TRACING", "false")

import functools
import http.server
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
import pytest_asyncio

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def demo_app_base_url() -> Iterator[str]:
    class _QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002 — matches BaseHTTPRequestHandler signature
            pass

    # NOTE: setting `directory` as a class attribute on SimpleHTTPRequestHandler does NOT
    # work — its __init__ always does `self.directory = directory or os.getcwd()`, which
    # creates an instance attribute that shadows the class attribute on every request,
    # silently falling back to the process's cwd (causing 404s for every real file). The
    # documented way to bind a serving directory is via functools.partial's `directory=`
    # kwarg, which __init__ actually reads.
    handler = functools.partial(_QuietHandler, directory=str(FIXTURES_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    port = server.server_address[1]
    yield f"http://127.0.0.1:{port}/"

    server.shutdown()
    server.server_close()


@pytest_asyncio.fixture
async def small_browser_pool(monkeypatch):
    """A real Playwright BrowserPool, sized down to 1 for a single e2e test rather than the
    production default of 4 concurrent browsers."""
    from app.execution.browser_pool import BrowserPool

    pool = BrowserPool(size=1, headless=True)
    await pool.start()

    monkeypatch.setattr("app.agents.executors.web.playwright_executor.get_browser_pool", lambda: pool)

    yield pool

    await pool.stop()
