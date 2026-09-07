from urllib.parse import urlparse
from src.fetching.raw_fetcher import RawFetcher
from src.schemas.v1 import AuditContext
from src.orchestration.errors import RecoverableError

async def retrieve_robots_txt(context: AuditContext, fetcher: RawFetcher) -> None:
    parsed = urlparse(str(context.target_url))
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    try:
        raw_page = await fetcher.fetch_page(robots_url, page_role="unknown")
        if raw_page.status_code == 200 and raw_page.html_content:
            # We enforce that the content_type is somewhat text-like, but some sites return weird headers.
            # We store whatever we decoded.
            context.robots_txt_content = raw_page.html_content
        else:
            context.robots_txt_content = None
            context.record_limitation(f"robots.txt fetch returned status {raw_page.status_code}")
    except RecoverableError as e:
        context.robots_txt_content = None
        context.record_limitation(f"Failed to fetch robots.txt: {e}")
