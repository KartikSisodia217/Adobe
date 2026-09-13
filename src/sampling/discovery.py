import asyncio
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from src.schemas.v1 import RawPage, PageRole
from src.fetching.raw_fetcher import RawFetcher
from src.security.url_normalize import normalize_url
from src.orchestration.errors import RecoverableError

def _is_same_registrable_domain(url1: str, url2: str) -> bool:
    host1 = urlparse(url1).hostname or ""
    host2 = urlparse(url2).hostname or ""
    
    if host1 == host2:
        return True
        
    def get_registrable(host: str) -> str:
        parts = host.split('.')
        if len(parts) <= 2:
            return host
        # Basic public suffix awareness without external dependencies
        dual_suffixes = {'co.uk', 'com.au', 'co.in', 'co.jp', 'com.br', 'org.uk', 'net.au'}
        if f"{parts[-2]}.{parts[-1]}" in dual_suffixes and len(parts) >= 3:
            return f"{parts[-3]}.{parts[-2]}.{parts[-1]}"
        return f"{parts[-2]}.{parts[-1]}"
        
    return get_registrable(host1) == get_registrable(host2)

async def discover_candidates(homepage_url: str, fetcher: RawFetcher, max_bfs_depth: int = 5, robots_txt: str = "") -> tuple[RawPage, set, list]:
    # 1. Fetch homepage
    try:
        homepage_raw = await fetcher.fetch_page(homepage_url, page_role="landing")
    except RecoverableError as e:
        raise RecoverableError(f"Homepage fetch failed: {e}")
        
    discovered_urls = set()
    sitemap_urls = []
    
    # BFS Queue
    queue = [homepage_raw]
    visited = {str(homepage_raw.url)}
    # max_bfs_depth is now an argument
    
    while queue and max_bfs_depth > 0:
        current_page = queue.pop(0)
        
        if current_page.html_content:
            soup = BeautifulSoup(current_page.html_content, 'lxml')
            for a in soup.find_all('a', href=True):
                href = a['href']
                try:
                    full_url = urljoin(str(current_page.url), href)
                    norm_url, _ = normalize_url(full_url, allow_http=True)
                    
                    if _is_same_registrable_domain(norm_url, homepage_url):
                        discovered_urls.add(norm_url)
                        # Optionally add to BFS queue if we haven't visited and have depth budget
                        if norm_url not in visited and len(visited) < 6:
                            visited.add(norm_url)
                            # Queue a fetch task! Wait, this is sequential.
                            # We can just fetch it right now.
                            try:
                                next_page = await fetcher.fetch_page(norm_url, page_role="unknown")
                                queue.append(next_page)
                                max_bfs_depth -= 1
                            except Exception:
                                pass
                except Exception:
                    continue

    # 2. Attempt sitemap
    parsed_home = urlparse(homepage_url)
    sitemap_url = f"{parsed_home.scheme}://{parsed_home.netloc}/sitemap.xml"
    sitemap_index_url = f"{parsed_home.scheme}://{parsed_home.netloc}/sitemap_index.xml"
    
    sitemap_urls_to_check = [sitemap_url, sitemap_index_url]
    if robots_txt:
        for line in robots_txt.splitlines():
            if line.lower().startswith("sitemap:"):
                sm_url = line.split(":", 1)[1].strip()
                if sm_url not in sitemap_urls_to_check:
                    sitemap_urls_to_check.append(sm_url)
    
    sitemap_content = None
    for s_url in sitemap_urls_to_check:
        try:
            s_page = await fetcher.fetch_page(s_url, page_role="unknown")
            if s_page.status_code == 200 and s_page.html_content:
                sitemap_content = s_page.html_content
                break
        except RecoverableError:
            continue
            
    if sitemap_content:
        soup = BeautifulSoup(sitemap_content, 'xml')
        for loc in soup.find_all('loc'):
            if loc.text:
                try:
                    norm_url, _ = normalize_url(loc.text, allow_http=True)
                    if _is_same_registrable_domain(norm_url, homepage_url):
                        sitemap_urls.append(norm_url)
                except Exception:
                    continue

    return homepage_raw, discovered_urls, sitemap_urls
