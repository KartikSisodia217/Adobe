import uuid
from datetime import datetime, timezone
from src.schemas.v1 import AuditContext
from pydantic import HttpUrl

def build_context(normalized_url: str) -> AuditContext:
    return AuditContext(
        audit_id=str(uuid.uuid4()),
        target_url=HttpUrl(normalized_url),
        started_at=datetime.now(timezone.utc),
        raw_pages=[],
        rendered_pages=[],
        coverage_notes=[],
        budgets_consumed={
            "raw_pages_fetched": 0,
            "pages_rendered": 0,
            "runtime_ms": 0,
            "wikidata_calls": 0
        }
    )
