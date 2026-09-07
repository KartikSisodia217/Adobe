from src.orchestration.logger import logger
import asyncio
import time
import json
from urllib.parse import urlparse
from src.orchestration.errors import FatalValidation, RecoverableError
from src.orchestration.context_builder import build_context
from src.security.url_normalize import normalize_url
from src.security.ssrf_guard import resolve_and_validate
from src.fetching.raw_fetcher import RawFetcher
from src.robots.robots_gate import retrieve_robots_txt
from src.sampling.discovery import discover_candidates
from src.sampling.candidate_selection import select_candidates
from src.browser.browser_host import BrowserHost
from src.browser.browser_adapter import BrowserAdapter, create_adapter
from src.schemas.v1 import RenderedPage, AuditReport, Summary, Coverage

# Stubs for M2/M3
async def run_m2(context): return []
async def run_m3_fact(context): return []
async def run_m3_engagement(adapter, context): return []

from src.fusion.normalize import normalize_findings
from src.fusion.dedupe import deduplicate_findings
from src.fusion.cross_signal import cross_validate_findings
from src.fusion.scoring import assign_severity_and_confidence
from src.fusion.cap import cap_findings
from src.reporting.report_builder import build_report, build_minimal_error_report

async def execute_audit(input_url: str) -> dict:
    start_time = time.monotonic()
    

    try:
        logger.info(f"Starting audit for {input_url}", extra={"phase": "start", "url": input_url})
        # 1-2. Validate & Normalize
        try:
            norm_url, _ = normalize_url(input_url, allow_http=True)
        except FatalValidation as e:
            return build_minimal_error_report(input_url, str(e)).model_dump(mode='json')

        # 3. Security Gate (SSRF / DNS)
        try:
            pinned_url, host = resolve_and_validate(norm_url, is_initial=True)
        except FatalValidation as e:
            return build_minimal_error_report(norm_url, str(e)).model_dump(mode='json')

        # 4. Context
        context = build_context(norm_url)
        fetcher = RawFetcher()
        
        try:
            # 5. Robots.txt
            await retrieve_robots_txt(context, fetcher)
            
            # 6-7. Discover
            homepage_raw, discovered, sitemaps = await discover_candidates(norm_url, fetcher)
            context.raw_pages.append(homepage_raw)
            context.budgets_consumed["raw_pages_fetched"] += 1
            
            # 8-9. Candidate Selection
            raw_cands, render_cands = select_candidates(homepage_raw, discovered, sitemaps)
            
            # 10. Raw Fetch Rest
            tasks = []
            for cand in raw_cands:
                if cand["url"] == str(homepage_raw.url):
                    continue
                tasks.append(fetcher.fetch_page(cand["url"], page_role=cand["role"]))
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    context.record_limitation(str(res))
                else:
                    context.raw_pages.append(res)
                    context.budgets_consumed["raw_pages_fetched"] += 1
                    
        finally:
            await fetcher.close()

        # 11-13. Render Subset
        host = BrowserHost()
        try:
            parsed_origin = urlparse(norm_url).hostname
            await host.start(allowed_origin=parsed_origin)
            
            for r_cand in render_cands:
                try:
                    render_data = await host.render_page(r_cand)
                    
                    # Find matching raw page
                    raw_matching = next((p for p in context.raw_pages if str(p.url) == r_cand["url"]), None)
                    if raw_matching:
                        r_page = RenderedPage(
                            **raw_matching.model_dump(),
                            accessibility_tree=render_data["accessibility_tree"],
                            rendered_html=render_data["rendered_html"]
                        )
                        context.rendered_pages.append(r_page)
                        context.budgets_consumed["pages_rendered"] += 1
                        
                        # 14. M3 Engagement
                        adapter = create_adapter(render_data["page"], render_data["accessibility_tree"])
                        try:
                            # Invoke M3 (stub)
                            await run_m3_engagement(adapter, context)
                        except Exception as e:
                            context.record_limitation(f"M3 engagement failed on {r_cand['url']}: {e}")
                            
                except RecoverableError as e:
                    context.record_limitation(str(e))
                finally:
                    if "page" in locals() and render_data.get("page"):
                        await render_data["page"].close()
                        
        except RecoverableError as e:
            context.record_limitation(str(e))
        finally:
            await host.cleanup()

        # M2 and M3 Fact (stubs)
        try:
            await run_m2(context)
            await run_m3_fact(context)
        except Exception as e:
            context.record_limitation(f"M2/M3 failed: {e}")

        # 15-21. Fusion (implemented next)
        raw_findings = [] # Collected from M2/M3
        norm_findings = normalize_findings(raw_findings)
        deduped = deduplicate_findings(norm_findings)
        cross = cross_validate_findings(deduped, context)
        scored = assign_severity_and_confidence(cross)
        final_findings, proactive = cap_findings(scored)

        # 22-23. Report Generation
        context.budgets_consumed["runtime_ms"] = int((time.monotonic() - start_time) * 1000)
        report = build_report(context, final_findings, proactive)
        

        logger.info("Audit complete", extra={"phase": "report_generation", "budget_consumption": context.budgets_consumed})
        return report.model_dump(mode='json')


    except Exception as e:
        # Fallback for unexpected bugs
        return build_minimal_error_report(input_url, f"Unexpected error: {str(e)}").model_dump(mode='json')
