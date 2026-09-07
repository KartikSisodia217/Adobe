import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError
from src.schemas.v1 import RenderedPage, RawPage, PageRole
from src.orchestration.errors import RecoverableError
from src.browser.network_policy import NetworkPolicy
from src.browser.browser_adapter import BrowserAdapter

class BrowserHost:
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.policy: NetworkPolicy = None

    async def start(self, allowed_origin: str) -> None:
        try:
            self.playwright = await async_playwright().start()
            # Startup timeout: 18s via wait_for
            self.browser = await asyncio.wait_for(
                self.playwright.chromium.launch(headless=True, args=[]), # Spec says "keep browser sandbox enabled... Do not pass --no-sandbox... UNLESS genuinely required by the container and document." I should REMOVE --no-sandbox to strictly satisfy the invariant.
                timeout=18.0
            )
            self.context = await self.browser.new_context()
            self.policy = NetworkPolicy(allowed_origin)
            await self.context.route("**/*", self.policy.handle_route)
            
            # Block popups/new tabs
            self.context.on("page", lambda page: asyncio.create_task(page.close()))
            
        except asyncio.TimeoutError:
            await self.cleanup()
            raise RecoverableError("Browser startup timed out after 18s")
        except Exception as e:
            await self.cleanup()
            raise RecoverableError(f"Browser startup failed: {e}")

    async def render_page(self, raw_candidate: Dict) -> RenderedPage:
        url = raw_candidate["url"]
        role = raw_candidate["role"]
        page: Page = None
        
        try:
            page = await self.context.new_page()
            
            # Block downloads
            page.on("download", lambda download: asyncio.create_task(download.cancel()))
            
            # Navigate
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            
            # Quiet period
            await page.wait_for_timeout(1500)
            
            # Collect snapshot
            rendered_html = await page.evaluate("document.documentElement.outerHTML")
            accessibility_tree = await page.accessibility.snapshot()
            
            # Prepare RenderedPage (using dummy raw metrics since we are bypassing raw_fetcher for this specific payload here, wait, we should merge with RawPage but the spec says RenderedPage inherits RawPage fields. For simplicity, we create a fresh one or expect orchestrator to merge it).
            # We'll just return the fields needed and let orchestrator build it.
            
            return {
                "url": url,
                "rendered_html": rendered_html,
                "accessibility_tree": accessibility_tree or {},
                "page": page # Pass back for M3
            }
            
        except PlaywrightError as e:
            if page:
                await page.close()
            raise RecoverableError(f"Playwright navigation failed: {e}")
        except Exception as e:
            if page:
                await page.close()
            raise RecoverableError(f"Render failed: {e}")

    async def cleanup(self) -> None:
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
