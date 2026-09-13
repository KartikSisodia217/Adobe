import asyncio
import time
import logging
from typing import List

from src.schemas.v1.context import AuditContext
from src.schemas.v1.findings import CandidateFinding
from src.schemas.v1.facts import StructuredFact
from src.security.url_normalize import normalize_url
from src.security.ssrf_guard import resolve_and_validate
from src.orchestration.errors import FatalValidation, RecoverableError
from src.orchestration.context_builder import build_context

from src.fetching.raw_fetcher import RawFetcher
from src.sampling.discovery import discover_candidates
from src.sampling.candidate_selection import select_render_candidates
from src.browser.browser_host import BrowserHost
from src.browser.browser_adapter import create_adapter
from src.schemas.v1 import RenderedPage

from src.access_content.auditor import run_access_content_audit
from src.fact_integrity.auditor import run_fact_integrity
from src.brand_identity.auditor import run_brand_identity_audit
from src.brand_identity.discovery import discover_external_sources
from src.engagement.engagement_auditor import run_interactive_tests

from src.fusion.normalize import normalize_findings
from src.fusion.dedupe import deduplicate_findings
from src.fusion.cross_signal import cross_validate_findings
from src.fusion.scoring import assign_severity_and_confidence
from src.fusion.cap import cap_findings
from src.reporting.report_builder import build_report, build_minimal_error_report

logger = logging.getLogger(__name__)

async def execute_audit(input_url: str, external_sources: list[dict] | None = None, discover_external_sources_enabled: bool = True) -> dict:
    start_time = time.monotonic()
    
    async def _do_audit() -> dict:
        logger.info(f"Starting audit for {input_url}", extra={"phase": "start", "url": input_url})
        try:
            norm_url, _ = normalize_url(input_url, allow_http=True)
        except FatalValidation as e:
            return build_minimal_error_report(input_url, str(e)).model_dump(mode='json')

        try:
            pinned_url, host = resolve_and_validate(norm_url, is_initial=True)
        except Exception as e:
            return build_minimal_error_report(input_url, str(e)).model_dump(mode='json')
            
        context = build_context(norm_url)
        context.target_url = pinned_url
        context.external_sources = external_sources or []
        fetcher = RawFetcher()
        
        try:
            # 6-7. Discovery & Adaptive Crawling (Phase 4 & 8)
            fetched_pages, discovered, sitemaps = await discover_candidates(norm_url, fetcher, max_discovery_pages=15)
            context.raw_pages.extend(fetched_pages)
            context.budgets_consumed["raw_pages_fetched"] += len(fetched_pages)
            
            discovered_external = await discover_external_sources(context.raw_pages, norm_url, enabled=discover_external_sources_enabled)
            context.external_sources.extend(discovered_external)
            
            # 11. Render Candidates (Semantic Sampling - Phase 5)
            render_cands = select_render_candidates(context.raw_pages)
        finally:
            await fetcher.close()

        # 11-13. Render Subset
        b_host = BrowserHost()
        raw_findings = []
        structured_facts = []
        try:
            for cand in render_cands:
                render_data = None
                try:
                    await b_host.start(str(context.target_url))
                    render_data = await b_host.render_page(str(cand.url), cand.page_role)
                    if render_data and render_data.get("rendered_html"):
                        html = render_data["rendered_html"]
                        a11y = render_data.get("accessibility_tree", {})
                        raw_matching = next((p for p in context.raw_pages if str(p.url) == str(cand.url)), None)
                        if raw_matching:
                            rp = RenderedPage(
                                **raw_matching.model_dump(),
                                accessibility_tree=a11y,
                                rendered_html=html
                            )
                            context.rendered_pages.append(rp)
                            context.budgets_consumed["pages_rendered"] += 1
                        
                        # 16-17. Engagement (Immediate, uses live page)
                        if render_data.get("page"):
                            try:
                                adapter = create_adapter(render_data["page"], a11y)
                                ef = await run_interactive_tests(adapter, context)
                                raw_findings.extend(ef)
                            except Exception as e:
                                context.record_limitation(f"Engagement eval failed for {rp.url}: {e}")
                            finally:
                                if 'adapter' in locals() and hasattr(adapter, 'stop'):
                                    await adapter.stop()
                                
                except Exception as e:
                    context.record_limitation(f"Failed to render {cand.url}: {e}")
                finally:
                    if render_data and render_data.get("page"):
                        try:
                            await render_data["page"].close()
                        except Exception:
                            pass
            
            # 14. Access Content (Phase 10: Role-aware detectors)
            ac_facts, ac_findings = run_access_content_audit(context)
            structured_facts.extend(ac_facts)
            raw_findings.extend(ac_findings)
            
            # 15. Fact Integrity
            fi_findings = await run_fact_integrity(context, structured_facts)
            raw_findings.extend(fi_findings)
            raw_findings.extend(run_brand_identity_audit(context))
            
        finally:
            await b_host.cleanup()
            
        # 18. Fusion
        normalized = normalize_findings(raw_findings)
        deduped = deduplicate_findings(normalized)
        cross_validated = cross_validate_findings(deduped, context)
        scored = assign_severity_and_confidence(cross_validated)
        final_findings, proactive, cap_stats = cap_findings(scored)
        context.budgets_consumed["suppressed_findings"] = cap_stats["suppressed"]
            
        context.budgets_consumed["runtime_ms"] = int((time.monotonic() - start_time) * 1000)
        
        # 19. Report Builder
        report = build_report(context, final_findings, proactive, cap_stats)
        logger.info("Audit complete", extra={"phase": "report_generation", "budget_consumption": context.budgets_consumed})
        return report.model_dump(mode='json')

    try:
        return await _do_audit()
    except Exception as e:
        logger.exception("Audit crashed unexpectedly")
        return build_minimal_error_report(input_url, f"Internal Error: {e}").model_dump(mode='json')
