import pytest
import json
import asyncio
from src.orchestration.orchestrator import execute_audit

@pytest.mark.asyncio
async def test_invalid_url_returns_minimal_report():
    report_dict = await execute_audit("http://localhost")
    assert "site" in report_dict
    assert report_dict["summary"]["total_findings"] == 0
    assert len(report_dict["coverage"]["limitations"]) > 0
    assert "private/local IP" in report_dict["coverage"]["limitations"][0] or "Localhost" in report_dict["coverage"]["limitations"][0]

@pytest.mark.asyncio
async def test_invalid_scheme_returns_minimal_report():
    report_dict = await execute_audit("file:///etc/passwd")
    assert "site" in report_dict
    assert report_dict["summary"]["total_findings"] == 0
    assert len(report_dict["coverage"]["limitations"]) > 0
    assert "scheme" in report_dict["coverage"]["limitations"][0]
