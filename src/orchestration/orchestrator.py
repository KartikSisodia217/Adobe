import asyncio
import time
import logging
from typing import List

from src.schemas.v1.context import AuditContext
from src.schemas.v1.findings import CandidateFinding
from src.schemas.v1.facts import StructuredFact
from src.security.url_normalize import normalize_url
from src.security.ssrf_guard import resolve_and_validate
from src.orchestration.errors import FatalValidation, FatalSecurity

from src.fetching.raw_fetcher import RawFetcher
from src.sampling.discovery import discover_candidates
from src.sampling.candidate_selection import select_render_candidates
from src.browser.browser_host import BrowserHost
from src.browser.browser_adapter import create_adapter
from src.schemas.v1 import RenderedPage

from src.access_content.auditor import run_access_content_audit
from src.fact_integrity.auditor import run_fact_integrity
from src.engagement.engagement_auditor import run_interactive_tests

from src.fusion.normalize import normalize_findings
from src.fusion.dedupe import deduplicate_findings
from src.fusion.cross_signal import cross_validate_findings
from src.fusion.scoring import assign_severity_and_confidence
from src.fusion.cap import cap_findings
from src.reporting.report_builder import build_report, build_minimal_error_report

logger = logging.getLogger(__name__)

async def execute_audit(input_url: str) -> dict:
    start_time = time.monotonic()
    
    async def _do_audit() -> dict:
        logger.info(f"Starting audit for {input_url}", extra={"phase": "start", "url": input_url})
        try:
            norm_url, _ = normalize_url(input_url, allow_http=True)
        except FatalValidation as e:
            return build_minimal_error_report(input_url, str(e)).model_dump(mode='json')

        try:
            pinned_url, host = resolve_and_validate(norm_url, is_initial=True)
        except FatalSecurity as e:
            return build_minimal_error_report(input_url, str(e)).model_dump(mode='json')
            
        context = AuditContext(target_url=pinned_url, host_ip=host)
        fetcher = RawFetcher()
        
        try:
            # 6-7. Discovery & Adaptive Crawling (Phase 4 & 8)
            fetched_pages, discovered, sitemaps = await discover_candidates(norm_url, fetcher, max_discovery_pages=15)
            context.raw_pages.extend(fetched_pages)
            context.budgets_consumed["raw_pages_fetched"] += len(fetched_pages)
            
            # 11. Render Candidates (Semantic Sampling - Phase 5)
            render_cands = select_render_candidates(context.raw_pages)
        finally:
            await fetcher.close()

        # 11-13. Render Subset
        b_host = BrowserHost()
        try:
            for cand in render_cands:
                try:
                    await b_host.ensure_started()
                    html, a11y = await b_host.render_page(str(cand.url), cand.page_role)
                    if html:
                        context.rendered_pages.append(RenderedPage(url=cand.url, page_role=cand.page_role, rendered_html=html, accessibility_tree=a11y))
                        context.budgets_consumed["pages_rendered"] += 1
                except Exception as e:
                    context.record_limitation(f"Failed to render {cand.url}: {e}")
            
            # 14. Access Content (Phase 10: Role-aware detectors)
            ac_facts, ac_findings = run_access_content_audit(context)
            context.facts.extend(ac_facts)
            context.findings.extend(ac_findings)
            
            # 15. Fact Integrity
            fi_findings = run_fact_integrity(context)
            context.findings.extend(fi_findings)
            
            # 16-17. Engagement
            eng_findings = []
            for rp in context.rendered_pages:
                try:
                    adapter = create_adapter(b_host.page, rp.accessibility_tree)
                    ef = await run_interactive_tests(adapter, context)
                    eng_findings.extend(ef)
                    if hasattr(adapter, 'stop'):
                        await adapter.stop()
                except Exception as e:
                    context.record_limitation(f"Engagement eval failed for {rp.url}: {e}")
            context.findings.extend(eng_findings)
            
        finally:
            await b_host.close()
            
        # 18. Fusion
        normalized = normalize_findings(context.findings)
        deduped = deduplicate_findings(normalized)
        cross_validated = cross_validate_findings(deduped, context)
        scored = assign_severity_and_confidence(cross_validated)
        final_findings, proactive, cap_stats = cap_findings(scored, context.proactive_suggestions)
        
        context.findings = final_findings
        context.proactive_suggestions = proactive
        if cap_stats:
            context.record_limitation(cap_stats)
            
        context.budgets_consumed["runtime_ms"] = int((time.monotonic() - start_time) * 1000)
        
        # 19. Report Builder
        report = build_report(context)
        logger.info("Audit complete", extra={"phase": "report_generation", "budget_consumption": context.budgets_consumed})
        return report.model_dump(mode='json')

    try:
        return await _do_audit()
    except Exception as e:
        logger.exception("Audit crashed unexpectedly")
        return build_minimal_error_report(input_url, f"Internal Error: {e}").model_dump(mode='json')
