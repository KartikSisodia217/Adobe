from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, HttpUrl, Field

PageRole = Literal["landing", "detail", "editorial", "contact", "index", "unknown"]

class RawPage(BaseModel):
    url: HttpUrl
    requested_url: HttpUrl
    status_code: int
    html_content: str
    headers: Dict[str, str]
    content_type: Optional[str] = None
    encoding: Optional[str] = None
    canonical_url: Optional[HttpUrl] = None
    page_role: PageRole
    size_bytes: int
    fetched_at: datetime
    truncated: bool

class RenderedPage(RawPage):
    accessibility_tree: Dict[str, Any]
    rendered_html: str
    console_errors: Optional[List[str]] = Field(default_factory=list)
