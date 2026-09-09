from datetime import datetime, timezone, date

import pytest
from pydantic import HttpUrl

from src.browser.browser_adapter import BrowserAdapter
from src.engagement.engagement_auditor import run_interactive_tests
from src.fact_integrity.auditor import run_fact_integrity
from src.schemas.v1 import AuditContext, StructuredFact


def context():
    return AuditContext(audit_id="m3", target_url=HttpUrl("https://example.com/"), started_at=datetime.now(timezone.utc),
                        raw_pages=[], rendered_pages=[], coverage_notes=[], budgets_consumed={"wikidata_calls": 0})


def fact(kind, value):
    return StructuredFact(fact_type=kind, value=value, source="raw_html", page_url=HttpUrl("https://example.com/"))


def adapter(tree, *, blocked=False, click_error=False, close_on_escape=False, close_on_click=False, trace=None):
    state = {"blocked": blocked}
    async def press(key):
        if close_on_escape and key == "Escape": state["blocked"] = False
    async def click(role, name):
        if click_error: raise RuntimeError("unreachable")
        if close_on_click and role == "button": state["blocked"] = False
    async def name(role): return None
    async def focus(limit): return (trace or ["modal-button"] * limit)[:limit]
    return BrowserAdapter(tree, press, click, name, focus, lambda: state["blocked"])


@pytest.mark.asyncio
async def test_g01_unnamed_essential_control():
    result = await run_interactive_tests(adapter({"role":"navigation", "children":[{"role":"button", "name":""}]}), context())
    assert [f.detector_id for f in result] == ["G-01"]


@pytest.mark.asyncio
async def test_g01_named_control_is_clean():
    result = await run_interactive_tests(adapter({"role":"navigation", "children":[{"role":"button", "name":"Menu"}]}), context())
    assert result == []


@pytest.mark.asyncio
async def test_g02_escape_closes_modal():
    tree = {"role":"dialog", "name":"Welcome"}
    assert await run_interactive_tests(adapter(tree, blocked=True, close_on_escape=True), context()) == []


@pytest.mark.asyncio
async def test_g02_safe_close_works():
    tree = {"role":"dialog", "name":"Welcome", "children":[{"role":"button", "name":"Close"}]}
    assert await run_interactive_tests(adapter(tree, blocked=True, close_on_click=True), context()) == []


@pytest.mark.asyncio
async def test_g02_genuine_focus_trap():
    tree = {"role":"dialog", "name":"Blocking", "children":[{"role":"button", "name":"Continue"}]}
    result = await run_interactive_tests(adapter(tree, blocked=True, trace=["one"] * 8), context())
    assert [f.detector_id for f in result] == ["G-02"]


@pytest.mark.asyncio
async def test_g03_reachable_and_broken_route():
    tree = {"role":"navigation", "children":[{"role":"link", "name":"About"}]}
    assert await run_interactive_tests(adapter(tree), context()) == []
    result = await run_interactive_tests(adapter(tree, click_error=True), context())
    assert [f.detector_id for f in result] == ["G-03"]


@pytest.mark.asyncio
async def test_fact_expired_and_consistent():
    result = await run_fact_integrity(context(), [fact("availability", "Offer expires 2020-01-01")], today=date(2021, 1, 1))
    assert [f.detector_id for f in result] == ["F-01"]
    assert await run_fact_integrity(context(), [fact("price", "$49")]) == []


@pytest.mark.asyncio
async def test_fact_contradiction_and_ambiguous_identity():
    result = await run_fact_integrity(context(), [fact("price", "$49"), fact("price", "$59")])
    assert [f.detector_id for f in result] == ["F-02"]
    result = await run_fact_integrity(context(), [fact("organization_name", "Company")])
    assert [f.detector_id for f in result] == ["F-03"]


@pytest.mark.asyncio
async def test_wikidata_timeout_and_failure_are_isolated():
    facts = [fact("organization_name", "Company"), fact("organization_name", "Brand")]
    async def timeout(_): raise __import__("asyncio").TimeoutError()
    audit = context()
    result = await run_fact_integrity(audit, facts, wikidata_lookup=timeout)
    assert any(f.detector_id == "F-02" for f in result)
    assert any("Wikidata lookup unavailable" in note for note in audit.coverage_notes)


@pytest.mark.asyncio
async def test_engagement_detector_failure_is_isolated():
    class BrokenAdapter:
        def get_accessibility_tree(self): return {"role":"navigation", "children":[{"role":"button", "name":""}, {"role":"link", "name":"About"}]}
        async def press(self, _): pass
        async def click(self, role, _):
            if role == "link": raise RuntimeError("bad route")
        def is_primary_route_blocked(self): return False
        async def bounded_focus_trace(self, max_steps=8): return []
    result = await run_interactive_tests(BrokenAdapter(), context())
    assert {f.detector_id for f in result} == {"G-01", "G-03"}
