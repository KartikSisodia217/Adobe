import re
from urllib.parse import urlparse
from playwright.async_api import Route, Request
from src.security.ssrf_guard import is_ip_safe

class NetworkPolicy:
    def __init__(self, allowed_origin: str):
        self.allowed_origin = allowed_origin

    async def handle_route(self, route: Route, request: Request):
        # 1. Method check
        if request.method.upper() != "GET":
            await route.abort()
            return
            
        # 2. Resource type checks
        if request.resource_type in ["websocket", "media", "manifest"]:
            await route.abort()
            return

        # 3. Scheme check
        parsed = urlparse(request.url)
        if parsed.scheme not in ("http", "https"):
            await route.abort()
            return

        # 4. Same origin check (default deny third party)
        if parsed.hostname != self.allowed_origin:
            await route.abort()
            return
            
        # All checks passed
        await route.continue_()
