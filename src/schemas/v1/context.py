from datetime import datetime
from typing import Optional, List, Dict, Union, Any
from pydantic import BaseModel, HttpUrl
from .pages import RawPage, RenderedPage

class AuditContext(BaseModel):
    audit_id: str
    target_url: HttpUrl
    started_at: datetime
    robots_txt_content: Optional[str] = None
    raw_pages: List[RawPage]
    rendered_pages: List[RenderedPage]
    coverage_notes: List[str]
    budgets_consumed: Dict[str, Union[int, float]]
    external_sources: List[Dict] = []
    query_simulation: List[Dict] = []
    config: Dict[str, Any] = {}

    def record_limitation(self, msg: str) -> None:
        self.coverage_notes.append(msg)
