"""Small, bounded public-source discovery for cross-web identity comparisons."""
from __future__ import annotations

import asyncio
from urllib.parse import quote_plus, urlparse
from urllib import robotparser

import aiohttp
from bs4 import BeautifulSoup

from src.security.ssrf_guard import resolve_and_validate


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _terms(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    candidates = [soup.find("meta", attrs={"property": "og:site_name"}), soup.find("title"), soup.find("h1")]
    values = [node.get("content") if node and node.has_attr("content") else node.get_text(" ", strip=True) if node else "" for node in candidates]
    return [" ".join(value.split())[:80] for value in values if value and len(value.strip()) > 2][:2]


async def discover_external_sources(raw_pages, target_url: str, *, enabled: bool, cap: int = 3) -> list[dict]:
    """Use at most two search queries and three GETs; never authenticate or submit data."""
    if not enabled:
        return []
    target_host = _host(target_url)
    queries = list(dict.fromkeys(term for page in raw_pages[:2] for term in _terms(page.html_content)))[:2]
    if not queries:
        return []
    timeout = aiohttp.ClientTimeout(total=4)
    urls: list[str] = []
    headers = {"User-Agent": "BrandIdentityAudit/1.0 (+read-only)"}
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for query in queries:
                async with session.get("https://html.duckduckgo.com/html/?q=" + quote_plus('"' + query + '"'), allow_redirects=False) as response:
                    if response.status != 200:
                        continue
                    soup = BeautifulSoup(await response.text(), "lxml")
                    for anchor in soup.select("a.result__a"):
                        href = anchor.get("href", "")
                        if href.startswith("http") and _host(href) != target_host and href not in urls:
                            urls.append(href)
                        if len(urls) >= cap:
                            break
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
        return []
    observations: list[dict] = []
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for url in urls[:cap]:
                try:
                    # Pin/validate each destination before public retrieval.
                    resolve_and_validate(url, is_initial=True)
                    origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    robots = robotparser.RobotFileParser()
                    async with session.get(origin + "/robots.txt", allow_redirects=False) as response:
                        robots.parse((await response.text()).splitlines() if response.status == 200 else [])
                    if not robots.can_fetch(headers["User-Agent"], url):
                        continue
                    async with session.get(url, allow_redirects=False) as response:
                        if response.status == 200 and "text/html" in response.headers.get("content-type", ""):
                            observations.append({"url": url, "html": await response.text(), "discovered_by": "bounded_public_search", "confidence": "low"})
                except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError):
                    continue
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
        pass
    return observations
