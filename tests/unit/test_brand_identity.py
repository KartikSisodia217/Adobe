from datetime import datetime, timezone

from pydantic import HttpUrl

from src.brand_identity.auditor import run_brand_identity_audit
from src.schemas.v1.context import AuditContext
from src.schemas.v1.pages import RawPage


def context(html: str, external_sources=None):
    page = RawPage(url=HttpUrl("https://official.example/"), requested_url=HttpUrl("https://official.example/"),
        status_code=200, html_content=html, headers={}, page_role="landing", size_bytes=len(html),
        fetched_at=datetime.now(timezone.utc), truncated=False)
    return AuditContext(audit_id="brand", target_url=HttpUrl("https://official.example/"), started_at=datetime.now(timezone.utc),
        raw_pages=[page], rendered_pages=[], coverage_notes=[], budgets_consumed={}, external_sources=external_sources or [])


OFFICIAL = '''<html><head><link rel="canonical" href="https://official.example/"><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Northstar","url":"https://official.example","sameAs":["https://www.linkedin.com/company/northstar"]}
</script></head><body><main><h1>Northstar</h1><p>This is the official website. All purchases are made through official.example.</p><a href="https://official.example/buy">Buy now</a></main></body></html>'''


def test_conflicting_action_url_is_critical_evidence():
    audit = context(OFFICIAL, [{"url": "https://old-market.example/northstar", "claims": {"purchase_destination": "https://old-market.example/buy"}, "timestamp": "2024-01-01"}])
    findings = run_brand_identity_audit(audit)
    conflict = next(f for f in findings if f.detector_id == "B-01")
    assert conflict.evidence_items[1]["value"] == "https://old-market.example/buy"
    assert audit.query_simulation and "official website" in audit.query_simulation[0]["question"]


def test_stale_fact_preserves_both_values():
    audit = context(OFFICIAL, [{"url": "https://directory.example/northstar", "claims": {"price": "$49"}}])
    # Add a first-party explicit price claim through supplied HTML, not an invented assumption.
    audit.raw_pages[0].html_content = OFFICIAL.replace("</main>", "<p>Price: $99</p></main>")
    findings = run_brand_identity_audit(audit)
    stale = next(f for f in findings if f.detector_id == "B-02")
    assert {item["value"] for item in stale.evidence_items} == {"$49", "$99"}


def test_same_name_entity_is_ambiguous_not_malicious():
    audit = context(OFFICIAL, [{"url": "https://unrelated.example/", "claims": {"organization_name": "Northstar"}}])
    findings = run_brand_identity_audit(audit)
    assert any(f.detector_id == "B-03" for f in findings)
    assert all("malicious" not in f.mechanism for f in findings)


def test_legitimate_sameas_or_no_conflict_is_clean():
    audit = context(OFFICIAL, [{"url": "https://www.linkedin.com/company/northstar", "claims": {"destination": "https://official.example/buy"}}])
    assert run_brand_identity_audit(audit) == []


def test_insufficient_evidence_does_not_invent_conflict():
    audit = context("<html><body><h1>Northstar</h1></body></html>")
    assert run_brand_identity_audit(audit) == []

def test_historical_platform_with_shared_identity_and_old_destination_conflicts():
    old = '''<script type="application/ld+json">{"@type":"Organization","name":"Northstar"}</script>
    <h1>Northstar Bootcamp</h1><a href="https://platform.example/checkout">Buy Northstar Bootcamp</a>'''
    audit = context(OFFICIAL, [{"url": "https://platform.example/northstar", "html": old}])
    findings = run_brand_identity_audit(audit)
    assert any(f.detector_id == "B-01" for f in findings)
