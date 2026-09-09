"""Run a deterministic Member 3 fixture-style audit and print findings as JSON."""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import HttpUrl

from src.browser.browser_adapter import BrowserAdapter
from src.engagement.engagement_auditor import run_interactive_tests
from src.fact_integrity.auditor import run_fact_integrity
from src.schemas.v1 import AuditContext, StructuredFact


async def main():
    context = AuditContext(audit_id="member3-prototype", target_url=HttpUrl("https://example.com/"),
        started_at=datetime.now(timezone.utc), raw_pages=[], rendered_pages=[], coverage_notes=[], budgets_consumed={"wikidata_calls": 0})
    async def noop(*_): return None
    async def trace(limit): return ["button"] * limit
    adapter = BrowserAdapter({"role":"navigation", "children":[{"role":"button", "name":""}]}, noop, noop, noop, trace, lambda: False)
    facts = [StructuredFact(fact_type="availability", value="Offer expires 2020-01-01", source="raw_html", page_url=context.target_url)]
    findings = await run_fact_integrity(context, facts) + await run_interactive_tests(adapter, context)
    print(json.dumps([item.model_dump(mode="json") for item in findings], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
