import pytest
from src.orchestration.orchestrator import execute_audit

@pytest.mark.asyncio
async def test_report_schema_contract_known_bad():
    report = await execute_audit("http://localhost")
    
    assert isinstance(report.get("site"), str)
    assert isinstance(report.get("audited_at"), str)
    assert report.get("audit_version") == "1.0.0"
    
    summary = report.get("summary", {})
    for key in ["total_findings", "critical", "high", "medium", "low", "proactive_suggestions", "narrative"]:
        assert key in summary
    assert summary["narrative"] is not None
    
    coverage = report.get("coverage", {})
    for key in ["pages_discovered", "pages_sampled_raw", "pages_rendered", "page_roles_sampled", "not_observed_roles", "limitations", "runtime_ms"]:
        assert key in coverage
        
    assert isinstance(report.get("findings"), list)
    assert isinstance(report.get("proactive_suggestions"), list)

@pytest.mark.asyncio
async def test_report_schema_contract_valid_unreachable():
    report = await execute_audit("http://nonexistent.domain.that.will.never.resolve.com")
    
    assert isinstance(report.get("site"), str)
    assert isinstance(report.get("audited_at"), str)
    assert report.get("audit_version") == "1.0.0"
    
    summary = report.get("summary", {})
    for key in ["total_findings", "critical", "high", "medium", "low", "proactive_suggestions", "narrative"]:
        assert key in summary
    assert summary["narrative"] is not None
    
    coverage = report.get("coverage", {})
    for key in ["pages_discovered", "pages_sampled_raw", "pages_rendered", "page_roles_sampled", "not_observed_roles", "limitations", "runtime_ms"]:
        assert key in coverage
        
    assert isinstance(report.get("findings"), list)
    assert isinstance(report.get("proactive_suggestions"), list)
