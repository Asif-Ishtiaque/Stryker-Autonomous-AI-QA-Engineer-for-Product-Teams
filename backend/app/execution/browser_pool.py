"""Playwright browser pool.

Cold-starting a Chromium process per run is the single biggest latency cost
in browser-based QA automation. This pool keeps N browser instances warm
(BROWSER_POOL_SIZE) and hands out fresh, isolated BrowserContexts per run —
so a run pays only for context creation (~tens of ms), not process launch
(~seconds). Contexts are always closed after use; the underlying Browser is
returned to the pool for reuse.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BrowserPool:
    def __init__(self, size: int, headless: bool) -> None:
        self._size = size
        self._headless = headless
        self._playwright: Playwright | None = None
        self._available: asyncio.Queue[Browser] = asyncio.Queue()
        self._started = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
            self._playwright = await async_playwright().start()
            for _ in range(self._size):
                browser = await self._playwright.chromium.launch(headless=self._headless)
                await self._available.put(browser)
            self._started = True
            logger.info("browser_pool.started", size=self._size)

    async def stop(self) -> None:
        if not self._started:
            return
        while not self._available.empty():
            browser = await self._available.get()
            await browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._started = False

    @asynccontextmanager
    async def acquire_context(self, **context_kwargs):
        if not self._started:
            await self.start()
        browser = await self._available.get()
        context: BrowserContext | None = None
        try:
            context = await browser.new_context(**context_kwargs)
            yield context
        finally:
            if context is not None:
                await context.close()
            await self._available.put(browser)


_pool: BrowserPool | None = None


def get_browser_pool() -> BrowserPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = BrowserPool(size=settings.browser_pool_size, headless=settings.browser_headless)
    return _pool
