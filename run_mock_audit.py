import asyncio
import json
from datetime import datetime
from pydantic import HttpUrl

from src.schemas.v1 import AuditContext, RawPage, RenderedPage
from src.access_content.auditor import run_access_content_audit
from src.fusion.normalize import normalize_findings
from src.fusion.dedupe import deduplicate_findings
from src.fusion.cross_signal import cross_validate_findings
from src.fusion.scoring import assign_severity_and_confidence
from src.fusion.cap import cap_findings
from src.reporting.report_builder import build_report

async def run_mock():
    # 1. Load broken fixtures to simulate a bad website
    with open("tests/fixtures/fixture_js_only.html", "r", encoding="utf-8") as f:
        raw_html = f.read()
    rendered_html = """
    <!DOCTYPE html><html><head><title>JS Only Example</title></head>
    <body><main><div id="product-container">
    <h1>Dynamic Product</h1><p>Price: $99.00</p>
    </div></main></body></html>
    """
    
    url = "https://mock-defective-site.com"
    raw_page = RawPage(
        url=HttpUrl(url), requested_url=HttpUrl(url), status_code=200,
        html_content=raw_html, headers={}, page_role="detail",
        size_bytes=len(raw_html), fetched_at=datetime.utcnow(), truncated=False
    )
    rendered_page = RenderedPage(
        url=HttpUrl(url), requested_url=HttpUrl(url), status_code=200,
        html_content=raw_html, headers={}, page_role="detail",
        size_bytes=len(rendered_html), fetched_at=datetime.utcnow(), truncated=False,
        accessibility_tree={}, rendered_html=rendered_html
    )
    
    context = AuditContext(
        audit_id="mock-1", target_url=HttpUrl(url), started_at=datetime.utcnow(),
        robots_txt_content="User-agent: OAI-SearchBot\nDisallow: /", # Simulate blocked AI bots
        raw_pages=[raw_page], rendered_pages=[rendered_page],
        coverage_notes=[], budgets_consumed={"raw_pages_fetched": 1, "pages_rendered": 1, "runtime_ms": 100}
    )

    # 2. Run your M2 Auditor
    facts, findings = run_access_content_audit(context)
    
    # 3. Run Fusion Engine (Member 1's code)
    norm = normalize_findings(findings)
    deduped = deduplicate_findings(norm)
    cross = cross_validate_findings(deduped, context)
    scored = assign_severity_and_confidence(cross)
    final, proactive = cap_findings(scored)
    
    # 4. Generate the Final Adobe Report
    report = build_report(context, final, proactive)
    print(json.dumps(report.model_dump(mode='json'), indent=2))

if __name__ == "__main__":
    asyncio.run(run_mock())
