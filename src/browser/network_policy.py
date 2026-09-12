import asyncio
import socket
from urllib.parse import urlparse
from playwright.async_api import Route, Request
from src.security.ssrf_guard import is_ip_safe

class NetworkPolicy:
    def __init__(self, allowed_origin: str):
        self.allowed_origin = allowed_origin
        self.dns_cache = {}

    async def _resolve_and_check_ssrf(self, hostname: str) -> bool:
        if hostname in self.dns_cache:
            return self.dns_cache[hostname]
            
        try:
            loop = asyncio.get_running_loop()
            ip = await loop.run_in_executor(None, socket.gethostbyname, hostname)
            is_safe = is_ip_safe(ip)
            self.dns_cache[hostname] = is_safe
            return is_safe
        except Exception:
            self.dns_cache[hostname] = False
            return False

    async def handle_route(self, route: Route, request: Request):
        # 1. Method check (allow standard web methods)
        if request.method.upper() not in ["GET", "OPTIONS", "HEAD", "POST"]:
            await route.abort()
            return
            
        # 2. Resource type checks
        if request.resource_type in ["websocket", "manifest"]:
            await route.abort()
            return

        # 3. Scheme check
        parsed = urlparse(request.url)
        if parsed.scheme not in ("http", "https"):
            await route.abort()
            return

        # 4. Universal SSRF protection on ALL browser requests
        is_safe = await self._resolve_and_check_ssrf(parsed.hostname)
        if not is_safe:
            await route.abort()
            return
            
        # All checks passed, allow the resource (including 3rd-party CDNs, APIs)
        await route.continue_()
