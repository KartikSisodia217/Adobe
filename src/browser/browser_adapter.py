from typing import Dict, Any, Optional, Callable, Awaitable, List

class BrowserAdapter:
    """
    Exposes strictly bounded operations to M3 without leaking Playwright instances.
    """
    def __init__(self,
                 accessibility_tree: Dict[str, Any],
                 press_fn: Callable[[str], Awaitable[None]],
                 click_fn: Callable[[str, str], Awaitable[None]],
                 computed_name_fn: Callable[[str], Awaitable[Optional[str]]],
                 trace_fn: Callable[[int], Awaitable[List[str]]],
                 route_blocked_fn: Callable[[], bool]):
        self._accessibility_tree = accessibility_tree
        self._press_fn = press_fn
        self._click_fn = click_fn
        self._computed_name_fn = computed_name_fn
        self._trace_fn = trace_fn
        self._route_blocked_fn = route_blocked_fn

    def get_accessibility_tree(self) -> Dict[str, Any]:
        return self._accessibility_tree

    async def press(self, key: str) -> None:
        await self._press_fn(key)

    async def click(self, role: str, name: str) -> None:
        await self._click_fn(role, name)

    async def get_computed_accessible_name(self, role: str) -> Optional[str]:
        return await self._computed_name_fn(role)

    def is_primary_route_blocked(self) -> bool:
        return self._route_blocked_fn()

    async def bounded_focus_trace(self, max_steps: int = 5) -> list:
        return await self._trace_fn(max_steps)

def create_adapter(page, accessibility_tree: Dict[str, Any]) -> BrowserAdapter:
    allowed_keys = {"Escape", "Tab", "Enter", "ArrowDown", "ArrowUp"}

    async def press_fn(key: str) -> None:
        if key not in allowed_keys:
            raise ValueError(f"Key {key} is not allowed")
        await page.keyboard.press(key)

    async def click_fn(role: str, name: str) -> None:
        locator = page.get_by_role(role, name=name).first
        await locator.click(timeout=3000)

    async def computed_name_fn(role: str) -> Optional[str]:
        locator = page.get_by_role(role).first
        try:
            return await locator.accessible_name()
        except Exception:
            return None

    def route_blocked_fn() -> bool:
        return False

    async def trace_fn(max_steps: int) -> List[str]:
        max_steps = min(max_steps, 12)
        trace = []
        for _ in range(max_steps):
            await page.keyboard.press("Tab")
            focused = await page.evaluate("document.activeElement.tagName")
            trace.append(focused)
        return trace

    return BrowserAdapter(
        accessibility_tree=accessibility_tree,
        press_fn=press_fn,
        click_fn=click_fn,
        computed_name_fn=computed_name_fn,
        trace_fn=trace_fn,
        route_blocked_fn=route_blocked_fn
    )
