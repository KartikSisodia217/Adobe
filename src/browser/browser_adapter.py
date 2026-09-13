import asyncio
from typing import Dict, Any, Optional, List

class BrowserAdapter:
    """
    Exposes strictly bounded operations to M3 without leaking Playwright instances.
    Uses an actor pattern to completely isolate the Playwright Page object, preventing
    access via closures, properties, or traversal.
    """
    def __init__(self, accessibility_tree: Dict[str, Any], queue: asyncio.Queue):
        self._accessibility_tree = accessibility_tree
        self._queue = queue

    def get_accessibility_tree(self) -> Dict[str, Any]:
        return self._accessibility_tree

    async def _send(self, action: str, **kwargs) -> Any:
        fut = asyncio.Future()
        await self._queue.put({"action": action, "kwargs": kwargs, "future": fut})
        return await fut

    async def get_url(self) -> str:
        return await self._send("get_url")

    async def is_destination_healthy(self) -> bool:
        return await self._send("is_destination_healthy")

    async def press(self, key: str) -> None:
        await self._send("press", key=key)

    async def click(self, role: str, name: str) -> None:
        await self._send("click", role=role, name=name)

    async def get_computed_accessible_name(self, role: str) -> Optional[str]:
        return await self._send("get_computed_accessible_name", role=role)

    async def is_primary_route_blocked(self) -> bool:
        return await self._send("is_primary_route_blocked")

    async def bounded_focus_trace(self, max_steps: int = 5) -> list:
        return await self._send("bounded_focus_trace", max_steps=max_steps)


def create_adapter(page, accessibility_tree: Dict[str, Any]) -> BrowserAdapter:
    queue = asyncio.Queue()
    allowed_keys = {"Escape", "Tab", "Enter", "ArrowDown", "ArrowUp"}

    async def actor():
        while True:
            msg = await queue.get()
            action = msg["action"]
            kwargs = msg["kwargs"]
            fut = msg["future"]

            try:
                if action == "stop":
                    fut.set_result(None)
                    break
                elif action == "get_url":
                    fut.set_result(page.url)
                elif action == "press":
                    key = kwargs["key"]
                    if key not in allowed_keys:
                        raise ValueError(f"Key {key} is not allowed")
                    await page.keyboard.press(key)
                    fut.set_result(None)
                elif action == "click":
                    locator = page.get_by_role(kwargs["role"], name=kwargs["name"]).first
                    await locator.click(timeout=3000)
                    fut.set_result(None)
                elif action == "get_computed_accessible_name":
                    locator = page.get_by_role(kwargs["role"]).first
                    try:
                        name = await locator.accessible_name()
                        fut.set_result(name)
                    except Exception:
                        fut.set_result(None)
                elif action == "is_primary_route_blocked":
                    res = await page.evaluate('''() => {
                        const hasModal = document.querySelectorAll('dialog[open], [aria-modal="true"]').length > 0;
                        const isBodyInert = document.body.inert;
                        const isBodyHidden = window.getComputedStyle(document.body).overflow === 'hidden';
                        return hasModal || isBodyInert || isBodyHidden;
                    }''')
                    fut.set_result(res)
                elif action == "is_destination_healthy":
                    res = await page.evaluate('''() => {
                        const text = document.body.innerText.toLowerCase();
                        if (text.includes("404 not found") || text.includes("page not found") || text.includes("file not found") || text.includes("error code: 404")) return false;
                        return document.querySelectorAll('h1, main, article').length > 0;
                    }''')
                    fut.set_result(res)
                elif action == "bounded_focus_trace":
                    max_steps = min(kwargs["max_steps"], 12)
                    trace = []
                    for _ in range(max_steps):
                        await page.keyboard.press("Tab")
                        focused = await page.evaluate("document.activeElement.tagName")
                        trace.append(focused)
                    fut.set_result(trace)
                else:
                    fut.set_exception(ValueError(f"Unknown action {action}"))
            except Exception as e:
                if not fut.done():
                    fut.set_exception(e)

    # Start the actor in the background
    task = asyncio.create_task(actor())

    # We need a way to clean up the actor when we're done. 
    # We will attach the cleanup to the page close or handle it externally.
    # We can patch the adapter with a stop method that the orchestrator calls.
    adapter = BrowserAdapter(accessibility_tree, queue)
    adapter._actor_task = task
    
    async def stop_actor():
        fut = asyncio.Future()
        await queue.put({"action": "stop", "kwargs": {}, "future": fut})
        await fut
        await task

    adapter.stop = stop_actor
    return adapter
