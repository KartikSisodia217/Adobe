import asyncio
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from src.schemas.v1 import RawPage, PageRole
from src.fetching.raw_fetcher import RawFetcher
from src.security.url_normalize import normalize_url
from src.orchestration.errors import RecoverableError

async def discover_candidates(homepage_url: str, fetcher: RawFetcher) -> tuple[RawPage, set, list]:
    # 1. Fetch homepage
    try:
        homepage_raw = await fetcher.fetch_page(homepage_url, page_role="landing")
    except RecoverableError as e:
        raise RecoverableError(f"Homepage fetch failed: {e}")
        
    discovered_urls = set()
    sitemap_urls = []
    
    # Extract links from homepage
    if homepage_raw.html_content:
        soup = BeautifulSoup(homepage_raw.html_content, 'lxml')
        for a in soup.find_all('a', href=True):
            href = a['href']
            try:
                full_url = urljoin(str(homepage_raw.url), href)
                norm_url, _ = normalize_url(full_url, allow_http=True)
                
                # Must be same-registrable-domain (for simplicity, same hostname)
                if urlparse(norm_url).hostname == urlparse(str(homepage_raw.url)).hostname:
                    discovered_urls.add(norm_url)
            except Exception:
                continue

    # 2. Attempt sitemap
    parsed_home = urlparse(homepage_url)
    sitemap_url = f"{parsed_home.scheme}://{parsed_home.netloc}/sitemap.xml"
    sitemap_index_url = f"{parsed_home.scheme}://{parsed_home.netloc}/sitemap_index.xml"
    
    sitemap_content = None
    for s_url in [sitemap_url, sitemap_index_url]:
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
                    if urlparse(norm_url).hostname == urlparse(str(homepage_raw.url)).hostname:
                        sitemap_urls.append(norm_url)
                except Exception:
                    continue

    return homepage_raw, discovered_urls, sitemap_urls
