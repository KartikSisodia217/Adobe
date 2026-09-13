from datetime import datetime, timezone
import pytest
from pydantic import HttpUrl

from src.brand_identity.auditor import run_brand_identity_audit
from src.schemas.v1.context import AuditContext
from src.schemas.v1.pages import RawPage


def context(html: str, external_sources=None, target_url: str = "https://official.example/"):
    page = RawPage(
        url=HttpUrl(target_url),
        requested_url=HttpUrl(target_url),
        status_code=200,
        html_content=html,
        headers={},
        page_role="landing",
        size_bytes=len(html),
        fetched_at=datetime.now(timezone.utc),
        truncated=False
    )
    return AuditContext(
        audit_id="brand-test",
        target_url=HttpUrl(target_url),
        started_at=datetime.now(timezone.utc),
        raw_pages=[page],
        rendered_pages=[],
        coverage_notes=[],
        budgets_consumed={},
        external_sources=list(external_sources or [])
    )


OFFICIAL = '''<html>
<head>
    <link rel="canonical" href="https://official.example/">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Northstar",
        "url": "https://official.example",
        "sameAs": ["https://www.youtube.com/@northstar", "https://x.com/northstar_official"]
    }
    </script>
</head>
<body>
    <main>
        <h1>Northstar</h1>
        <p>This is the official website of Northstar. All official enrollments and purchases are made through official.example.</p>
        <p>Official Price: ₹7,999</p>
        <a href="https://official.example/enroll">Enroll in Northstar Bootcamp</a>
    </main>
</body>
</html>'''


# --------------------------------------------------------------------------
# Scenario 1: Same brand + official and stale external source
# --------------------------------------------------------------------------
def test_same_brand_official_and_stale_external_source():
    """Identifies historical platform representation that still routes actions independently."""
    stale_platform_html = '''<html>
    <head><title>Northstar on LegacyHost</title></head>
    <body>
        <h1>Northstar</h1>
        <p>Welcome to Northstar classes.</p>
        <a href="https://www.youtube.com/@northstar">YouTube</a>
        <a href="https://legacyhost.example/checkout">Purchase Northstar Course</a>
    </body>
    </html>'''
    audit = context(OFFICIAL, [{"url": "https://legacyhost.example/northstar", "html": stale_platform_html}])
    findings = run_brand_identity_audit(audit)

    # Must classify source as historical first-party
    ext_source = audit.external_sources[0]
    assert ext_source.get("classification") == "historical first-party"
    assert any(c["anchor"] == "shared_social_channel" for c in ext_source.get("connecting_evidence", []))

    # Must detect conflicting destination (B-01) and/or outdated platform representation (B-05)
    b01 = next((f for f in findings if f.detector_id == "B-01"), None)
    assert b01 is not None
    assert any("https://legacyhost.example/checkout" in str(ev.get("value")) for ev in b01.evidence_items)


# --------------------------------------------------------------------------
# Scenario 2: Same brand + legitimate third-party reseller
# --------------------------------------------------------------------------
def test_same_brand_legitimate_third_party_reseller():
    """Third-party authorized reseller with clear disclosure does not produce false positive impersonation."""
    reseller_html = '''<html>
    <head><title>Authorized Partner - Northstar</title></head>
    <body>
        <h1>Northstar Products</h1>
        <p>We are an authorized reseller and official partner of Northstar.</p>
        <a href="https://reseller.example/cart">Order via Partner</a>
    </body>
    </html>'''
    audit = context(OFFICIAL, [{"url": "https://reseller.example/store", "html": reseller_html}])
    findings = run_brand_identity_audit(audit)

    ext_source = audit.external_sources[0]
    assert ext_source.get("classification") == "reseller"
    # Must NOT classify as scam, malicious, or B-03 entity ambiguity
    assert not any(f.detector_id == "B-03" for f in findings)


# --------------------------------------------------------------------------
# Scenario 3: Same-name but unrelated company
# --------------------------------------------------------------------------
def test_same_name_unrelated_company():
    """Unrelated company with same name surfaces neutral entity ambiguity, never scam accusations."""
    unrelated_html = '''<html>
    <head><title>Northstar HVAC & Plumbing</title></head>
    <body>
        <h1>Northstar</h1>
        <p>Commercial HVAC services in Ohio since 1995.</p>
        <a href="https://unrelated-hvac.example/contact">Contact Us</a>
    </body>
    </html>'''
    audit = context(OFFICIAL, [{"url": "https://unrelated-hvac.example/", "html": unrelated_html}])
    findings = run_brand_identity_audit(audit)

    b03 = next((f for f in findings if f.detector_id == "B-03"), None)
    assert b03 is not None
    assert b03.mechanism == "same-name entity ambiguity"
    # Verify neutral evidence-backed language
    assert all("scam" not in str(ev).lower() and "malicious" not in str(ev).lower() for ev in b03.evidence_items)


# --------------------------------------------------------------------------
# Scenario 4: Historical page explicitly marked historical
# --------------------------------------------------------------------------
def test_historical_page_explicitly_marked_historical():
    """Historical page with migration notice acknowledges predecessor status."""
    migrated_html = '''<html>
    <head><title>Northstar - Old Portal</title></head>
    <body>
        <h1>Northstar</h1>
        <p>Notice: This legacy platform is no longer active. We have moved and migrated to our new domain.</p>
        <a href="https://official.example/">Go to Official Website</a>
    </body>
    </html>'''
    audit = context(OFFICIAL, [{"url": "https://oldportal.example/archive", "html": migrated_html}])
    findings = run_brand_identity_audit(audit)

    ext_source = audit.external_sources[0]
    assert ext_source.get("classification") == "historical first-party"
    # Because it directs users to official.example and has migration notice, B-01 does not fire
    assert not any(f.detector_id == "B-01" for f in findings)


# --------------------------------------------------------------------------
# Scenario 5: Conflicting price
# --------------------------------------------------------------------------
def test_conflicting_price():
    """Surfaces price discrepancy between official and external listings without calling either fraudulent."""
    external_store = '''<html>
    <head><title>Northstar Courses</title></head>
    <body>
        <h1>Northstar Course</h1>
        <p>Price: ₹4,999</p>
        <a href="https://marketplace.example/northstar">View Listing</a>
    </body>
    </html>'''
    audit = context(OFFICIAL, [{"url": "https://marketplace.example/northstar", "html": external_store}])
    findings = run_brand_identity_audit(audit)

    b02 = next((f for f in findings if f.detector_id == "B-02"), None)
    assert b02 is not None
    assert b02.mechanism == "potentially stale or conflicting fact"
    values = {ev.get("value") for ev in b02.evidence_items if "value" in ev}
    assert "₹7,999" in values
    assert "₹4,999" in values


# --------------------------------------------------------------------------
# Scenario 6: Conflicting purchase destination
# --------------------------------------------------------------------------
def test_conflicting_purchase_destination():
    """Flags external purchase destination pointing away from authoritative domain."""
    audit = context(
        OFFICIAL,
        [{
            "url": "https://thirdparty-checkout.example/item",
            "claims": {"purchase_destination": "https://thirdparty-checkout.example/pay"},
            "timestamp": "2024-06-01"
        }]
    )
    findings = run_brand_identity_audit(audit)
    b01 = next((f for f in findings if f.detector_id == "B-01"), None)
    assert b01 is not None
    assert b01.category == "brand-identity"
    assert any("thirdparty-checkout.example" in str(ev.get("value")) for ev in b01.evidence_items)


# --------------------------------------------------------------------------
# Scenario 7: No external conflict
# --------------------------------------------------------------------------
def test_no_external_conflict():
    """Verified social profile and compliant links produce zero conflicts."""
    social_profile = '''<html>
    <head><title>Northstar Official Channel</title></head>
    <body>
        <h1>Northstar</h1>
        <a href="https://official.example/enroll">Visit Official Site to Enroll</a>
    </body>
    </html>'''
    audit = context(OFFICIAL, [{"url": "https://www.youtube.com/@northstar", "html": social_profile}])
    findings = run_brand_identity_audit(audit)
    # No conflicts should be found
    assert len(findings) == 0


# --------------------------------------------------------------------------
# Scenario 8: Insufficient evidence
# --------------------------------------------------------------------------
def test_insufficient_evidence_does_not_invent_conflict():
    """Minimal page with no external evidence returns zero conflicts and does not fabricate findings."""
    audit = context("<html><body><h1>Northstar</h1><p>Simple description.</p></body></html>", external_sources=[])
    findings = run_brand_identity_audit(audit)
    assert findings == []
