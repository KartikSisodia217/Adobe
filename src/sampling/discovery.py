import asyncio
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Tuple, List, Set
from src.schemas.v1 import RawPage, PageRole
from src.fetching.raw_fetcher import RawFetcher
from src.security.url_normalize import normalize_url
from src.orchestration.errors import RecoverableError

def _is_same_registrable_domain(url1: str, url2: str) -> bool:
    host1 = urlparse(url1).hostname or ""
    host2 = urlparse(url2).hostname or ""
    
    if host1 == host2: return True
        
    def get_registrable(host: str) -> str:
        parts = host.split('.')
        if len(parts) <= 2: return host
        dual_suffixes = {'co.uk', 'com.au', 'co.in', 'co.jp', 'com.br', 'org.uk', 'net.au'}
        if f"{parts[-2]}.{parts[-1]}" in dual_suffixes and len(parts) >= 3:
            return f"{parts[-3]}.{parts[-2]}.{parts[-1]}"
        return f"{parts[-2]}.{parts[-1]}"
        
    return get_registrable(host1) == get_registrable(host2)

async def discover_candidates(homepage_url: str, fetcher: RawFetcher, max_discovery_pages: int = 15) -> Tuple[List[RawPage], Set[str], List[str]]:
    fetched_pages = []
    discovered_urls = set()
    sitemap_urls = []
    
    try:
        homepage_raw = await fetcher.fetch_page(homepage_url, page_role="landing")
        fetched_pages.append(homepage_raw)
    except RecoverableError as e:
        raise RecoverableError(f"Homepage fetch failed: {e}")
    
    queue = [homepage_raw]
    visited = {str(homepage_raw.url)}
    
    while queue and len(fetched_pages) < max_discovery_pages:
        current_page = queue.pop(0)
        if not current_page.html_content: continue
        
        soup = BeautifulSoup(current_page.html_content, 'lxml')
        for a in soup.find_all('a', href=True):
            try:
                norm_url, _ = normalize_url(urljoin(str(current_page.url), a['href']), allow_http=True)
                if _is_same_registrable_domain(norm_url, homepage_url):
                    discovered_urls.add(norm_url)
                    if norm_url not in visited and len(visited) < max_discovery_pages:
                        visited.add(norm_url)
                        try:
                            nxt = await fetcher.fetch_page(norm_url, page_role="unknown")
                            fetched_pages.append(nxt)
                            queue.append(nxt)
                            if len(fetched_pages) >= max_discovery_pages: break
                        except Exception:
                            pass
            except Exception:
                continue

    parsed_home = urlparse(homepage_url)
    for s_url in [f"{parsed_home.scheme}://{parsed_home.netloc}/sitemap.xml", f"{parsed_home.scheme}://{parsed_home.netloc}/sitemap_index.xml"]:
        try:
            s_page = await fetcher.fetch_page(s_url, page_role="unknown")
            if s_page.status_code == 200 and s_page.html_content:
                soup = BeautifulSoup(s_page.html_content, 'xml')
                for loc in soup.find_all('loc'):
                    if loc.text:
                        try:
                            norm_url, _ = normalize_url(loc.text, allow_http=True)
                            if _is_same_registrable_domain(norm_url, homepage_url):
                                sitemap_urls.append(norm_url)
                        except Exception:
                            continue
                break
        except Exception:
            continue

    return fetched_pages, discovered_urls, sitemap_urls
