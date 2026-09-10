import pytest
from pydantic import HttpUrl
from datetime import datetime
import json

from src.schemas.v1.context import AuditContext
from src.schemas.v1.pages import RawPage, RenderedPage
from src.access_content.auditor import run_access_content_audit

def create_context(html_content: str, rendered_html: str = None, url: str = "https://example.com") -> AuditContext:
    raw_page = RawPage(
        url=HttpUrl(url),
        requested_url=HttpUrl(url),
        status_code=200,
        html_content=html_content,
        headers={},
        page_role="detail",
        size_bytes=len(html_content),
        fetched_at=datetime.utcnow(),
        truncated=False
    )
    
    rendered_pages = []
    if rendered_html is not None:
        rendered_pages.append(RenderedPage(
            url=HttpUrl(url),
            requested_url=HttpUrl(url),
            status_code=200,
            html_content=html_content, # original html
            headers={},
            page_role="detail",
            size_bytes=len(rendered_html),
            fetched_at=datetime.utcnow(),
            truncated=False,
            accessibility_tree={},
            rendered_html=rendered_html
        ))
        
    return AuditContext(
        audit_id="test-1",
        target_url=HttpUrl(url),
        started_at=datetime.utcnow(),
        raw_pages=[raw_page],
        rendered_pages=rendered_pages,
        coverage_notes=[],
        budgets_consumed={}
    )

def test_clean_ssr_fixture():
    with open("tests/fixtures/fixture_clean_ssr.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    # Clean SSR should have same raw and rendered
    context = create_context(html, html)
    facts, findings = run_access_content_audit(context)
    
    # Should have 0 findings
    assert len(findings) == 0, f"Expected 0 findings, got {len(findings)}: {findings}"
    
    # Should extract price and availability
    price_facts = [f for f in facts if f.fact_type == "price"]
    assert len(price_facts) >= 1
    assert any(f.value == "49.0" for f in price_facts)

def test_js_only_fixture():
    with open("tests/fixtures/fixture_js_only.html", "r", encoding="utf-8") as f:
        raw_html = f.read()
        
    rendered_html = """
    <!DOCTYPE html><html><head><title>JS Only Example</title></head>
    <body><main><div id="product-container">
    <h1>Dynamic Product</h1><p>Price: $99.00</p>
    </div></main></body></html>
    """
    
    context = create_context(raw_html, rendered_html)
    facts, findings = run_access_content_audit(context)
    
    # Should trigger E-01
    assert any(f.detector_id == "E-01" for f in findings), "Expected E-01 JS Rendering Gap finding"

def test_schema_conflict_fixture():
    with open("tests/fixtures/fixture_schema_conflict.html", "r", encoding="utf-8") as f:
        html = f.read()
        
    context = create_context(html, html)
    facts, findings = run_access_content_audit(context)
    
    # Should trigger D-02
    assert any(f.detector_id == "D-02" for f in findings), "Expected D-02 Schema Contradiction finding"
    
def test_robots_txt_denied():
    context = AuditContext(
        audit_id="test-robots",
        target_url=HttpUrl("https://example.com"),
        started_at=datetime.utcnow(),
        robots_txt_content="User-agent: OAI-SearchBot\nDisallow: /",
        raw_pages=[],
        rendered_pages=[],
        coverage_notes=[],
        budgets_consumed={}
    )
    
    facts, findings = run_access_content_audit(context)
    assert any(f.detector_id == "D-01" for f in findings), "Expected D-01 Retrieval Access finding"

