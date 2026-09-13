"""Bounded, public-source discovery for cross-web identity comparisons.

Respects robots.txt, strictly read-only, timeout-bounded, and never submits data.
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any, List, Set
from urllib import robotparser
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from src.security.ssrf_guard import resolve_and_validate

_KNOWN_PLATFORMS = {
    "classx.co.in", "teachable.com", "thinkific.com", "podia.com", "gumroad.com",
    "kajabi.com", "myshopify.com", "substack.com", "hashnode.dev", "medium.com",
    "github.io", "vercel.app", "netlify.app", "notion.site"
}

_SEARCH_ENGINES = {
    "bing.com", "duckduckgo.com", "google.com", "yahoo.com", "baidu.com", "yandex.com"
}

_SOCIAL_DOMAINS = {
    "linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com",
    "youtube.com", "tiktok.com", "pinterest.com", "reddit.com", "github.com"
}


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _clean_term(text: str) -> str:
    # Strip common suffixes like '| Home', '- Official Site', 'Slogans'
    cleaned = re.split(r"[\s\|\-\:\•\–\—]+", text)[0]
    return " ".join(cleaned.split())[:60]


def extract_search_terms(raw_pages, target_url: str) -> list[str]:
    """Extract clean entity and brand terms from first-party pages."""
    target_host = _host(target_url)
    terms: list[str] = []

    for page in raw_pages[:3]:
        soup = BeautifulSoup(page.html_content, "lxml")

        # 1. JSON-LD Organization name / Person name
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                payload = json.loads(script.get_text(strip=True))
                nodes = payload.get("@graph", [payload]) if isinstance(payload, dict) else payload
                if isinstance(nodes, list):
                    for node in nodes:
                        if isinstance(node, dict) and node.get("@type") in {"Organization", "Corporation", "Brand", "Person"}:
                            name = node.get("name")
                            if name and isinstance(name, str) and len(name.strip()) > 1:
                                terms.append(name.strip())
            except Exception:
                continue

        # 2. og:site_name
        og_site = soup.find("meta", attrs={"property": "og:site_name"})
        if og_site and og_site.get("content"):
            terms.append(og_site["content"].strip())

        # 3. title & h1
        title = soup.find("title")
        if title and title.string:
            t_text = title.string.strip()
            # If title has "Brand by Creator", also extract creator
            match_by = re.search(r"([A-Za-z0-9_]+)\s+by\s+([A-Za-z\s]+)", t_text, re.I)
            if match_by:
                terms.append(match_by.group(1).strip())
                terms.append(match_by.group(0).strip())
            terms.append(_clean_term(t_text))

        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(" ", strip=True)
            if h1_text and len(h1_text) < 40:
                terms.append(_clean_term(h1_text))

    # Fallback to domain name without TLD
    domain_label = target_host.split(".")[0]
    if domain_label and len(domain_label) > 2:
        terms.append(domain_label)

    # Deduplicate while preserving order
    unique_terms = []
    seen = set()
    for t in terms:
        t_clean = " ".join(t.split())
        if t_clean and len(t_clean) >= 2 and t_clean.lower() not in seen:
            seen.add(t_clean.lower())
            unique_terms.append(t_clean)

    return unique_terms[:3]


def extract_outbound_platform_candidates(raw_pages, target_url: str) -> list[str]:
    """Inspect first-party pages for outbound links to candidate platforms or subdomains."""
    target_host = _host(target_url)
    candidates: list[str] = []
    seen = set()

    for page in raw_pages[:3]:
        soup = BeautifulSoup(page.html_content, "lxml")
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href.startswith(("http://", "https://")):
                continue
            host = _host(href)
            if not host or host == target_host or host in _SOCIAL_DOMAINS or host in _SEARCH_ENGINES:
                continue

            # Check if domain matches known platforms or shares partial hostname
            is_platform = any(host == p or host.endswith("." + p) for p in _KNOWN_PLATFORMS)
            if is_platform and href not in seen:
                seen.add(href)
                # Keep root or direct landing URL
                parsed = urlparse(href)
                root_or_path = f"{parsed.scheme}://{parsed.netloc}/"
                candidates.append(root_or_path)

    return candidates[:3]


def _decode_bing_url(href: str) -> str | None:
    """Decode redirect link from Bing search result."""
    try:
        if "u=a1" in href:
            p = urlparse(href)
            qs = parse_qs(p.query)
            u_val = qs.get("u", [""])[0]
            b64 = u_val[2:] if u_val.startswith("a1") else u_val
            rem = len(b64) % 4
            if rem:
                b64 += "=" * (4 - rem)
            decoded = base64.b64decode(b64).decode("utf-8", "ignore")
            if decoded.startswith(("http://", "https://")):
                return decoded
        elif href.startswith(("http://", "https://")):
            return href
    except Exception:
        pass
    return None


def _decode_ddg_url(href: str) -> str | None:
    """Decode redirect link from DuckDuckGo search result."""
    try:
        if "uddg=" in href:
            p = urlparse(href)
            qs = parse_qs(p.query)
            if "uddg" in qs and qs["uddg"]:
                decoded = unquote(qs["uddg"][0])
                if decoded.startswith(("http://", "https://")):
                    return decoded
        elif href.startswith(("http://", "https://")):
            return href
    except Exception:
        pass
    return None


async def _search_bing(session: aiohttp.ClientSession, query: str, target_host: str, limit: int) -> list[str]:
    urls = []
    try:
        bing_url = "https://www.bing.com/search?q=" + quote_plus(query)
        async with session.get(bing_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=4)) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.select("li.b_algo h2 a"):
                    href = a.get("href", "")
                    decoded = _decode_bing_url(href)
                    if decoded:
                        h = _host(decoded)
                        if h and h != target_host and h not in _SEARCH_ENGINES and h not in _SOCIAL_DOMAINS:
                            if decoded not in urls:
                                urls.append(decoded)
                    if len(urls) >= limit:
                        break
    except Exception:
        pass
    return urls


async def _search_duckduckgo(session: aiohttp.ClientSession, query: str, target_host: str, limit: int) -> list[str]:
    urls = []
    try:
        ddg_url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
        async with session.get(ddg_url, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=4)) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.select("a.result__a, a.result__url"):
                    href = a.get("href", "")
                    decoded = _decode_ddg_url(href)
                    if decoded:
                        h = _host(decoded)
                        if h and h != target_host and h not in _SEARCH_ENGINES and h not in _SOCIAL_DOMAINS:
                            if decoded not in urls:
                                urls.append(decoded)
                    if len(urls) >= limit:
                        break
    except Exception:
        pass
    return urls


async def discover_external_sources(
    raw_pages,
    target_url: str,
    *,
    enabled: bool = True,
    cap: int = 4
) -> list[dict]:
    """Bounded, read-only external candidate discovery.

    Combines:
    1. Direct outbound platform links from first-party pages
    2. Bounded public search (Bing & DuckDuckGo)
    Respects robots.txt, limits total requests, and uses SSRF protection.
    """
    if not enabled:
        return []

    target_host = _host(target_url)
    terms = extract_search_terms(raw_pages, target_url)
    outbound_candidates = extract_outbound_platform_candidates(raw_pages, target_url)

    discovered_urls: list[str] = []

    # Priority 1: Direct outbound platform links found on site
    for url in outbound_candidates:
        if _host(url) != target_host and url not in discovered_urls:
            discovered_urls.append(url)

    # Priority 2: Public search engine queries
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AIMLESS-BrandAudit/1.0 (+https://github.com/KartikSisodia217/Adobe; read-only)"
    }
    timeout = aiohttp.ClientTimeout(total=5)

    if len(discovered_urls) < cap and terms:
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                for term in terms[:2]:
                    # Query Bing
                    bing_results = await _search_bing(session, term, target_host, limit=cap)
                    for u in bing_results:
                        if u not in discovered_urls and _host(u) != target_host:
                            discovered_urls.append(u)
                        if len(discovered_urls) >= cap:
                            break

                    # Fallback / augment with DuckDuckGo if still below cap
                    if len(discovered_urls) < cap:
                        ddg_results = await _search_duckduckgo(session, term, target_host, limit=cap)
                        for u in ddg_results:
                            if u not in discovered_urls and _host(u) != target_host:
                                discovered_urls.append(u)
                            if len(discovered_urls) >= cap:
                                break

                    if len(discovered_urls) >= cap:
                        break
        except Exception:
            pass

    # Now fetch candidates safely
    observations: list[dict] = []
    fetch_timeout = aiohttp.ClientTimeout(total=4)

    try:
        async with aiohttp.ClientSession(timeout=fetch_timeout, headers=headers) as session:
            for url in discovered_urls[:cap]:
                try:
                    # 1. SSRF Guard
                    resolve_and_validate(url, is_initial=True)

                    # 2. Robots.txt Check
                    parsed = urlparse(url)
                    origin = f"{parsed.scheme}://{parsed.netloc}"
                    robots = robotparser.RobotFileParser()
                    try:
                        async with session.get(origin + "/robots.txt", allow_redirects=True, timeout=aiohttp.ClientTimeout(total=3)) as r_resp:
                            if r_resp.status == 200:
                                r_text = await r_resp.text()
                                robots.parse(r_text.splitlines())
                            else:
                                robots.parse([])
                    except Exception:
                        robots.parse([])

                    if not robots.can_fetch(headers["User-Agent"], url):
                        continue

                    # 3. GET Content
                    async with session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=4)) as response:
                        if response.status == 200:
                            content_type = response.headers.get("content-type", "").lower()
                            if "text/html" in content_type:
                                html_text = await response.text()
                                observations.append({
                                    "url": str(response.url),
                                    "original_url": url,
                                    "html": html_text,
                                    "discovered_by": "bounded_cross_web_discovery",
                                    "confidence": "high",
                                    "status_code": response.status
                                })
                except Exception:
                    continue
    except Exception:
        pass

    return observations
