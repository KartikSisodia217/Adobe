from datetime import datetime, timezone
from typing import List, Dict
from src.schemas.v1 import AuditContext, FinalFinding, ProactiveSuggestion, AuditReport, Summary, Coverage, ExternalCalls

def build_report(context: AuditContext, findings: List[FinalFinding], proactive: List[ProactiveSuggestion]) -> AuditReport:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        if f.severity in counts:
            counts[f.severity] += 1
            
    summary = Summary(
        total_findings=len(findings),
        critical=counts["critical"],
        high=counts["high"],
        medium=counts["medium"],
        low=counts["low"],
        proactive_suggestions=len(proactive)
    )
    
    roles_sampled = list(set([p.page_role for p in context.raw_pages]))
    
    coverage = Coverage(
        pages_discovered=len(context.raw_pages), # Using fetched count for simplicity here
        pages_sampled_raw=context.budgets_consumed["raw_pages_fetched"],
        pages_rendered=context.budgets_consumed["pages_rendered"],
        page_roles_sampled=roles_sampled,
        not_observed_roles=[],
        limitations=context.coverage_notes,
        runtime_ms=context.budgets_consumed.get("runtime_ms", 0),
        external_calls=ExternalCalls(wikidata=context.budgets_consumed.get("wikidata_calls", 0))
    )
    
    return AuditReport(
        site=str(context.target_url),
        audited_at=datetime.now(timezone.utc).isoformat() + "Z",
        audit_version="1.0.0",
        summary=summary,
        coverage=coverage,
        findings=findings,
        proactive_suggestions=proactive
    )

def build_minimal_error_report(input_url: str, error_msg: str) -> AuditReport:
    # Build a minimal valid report for fatal errors
    return AuditReport(
        site=input_url,
        audited_at=datetime.now(timezone.utc).isoformat() + "Z",
        audit_version="1.0.0",
        summary=Summary(total_findings=0, critical=0, high=0, medium=0, low=0, proactive_suggestions=0),
        coverage=Coverage(
            pages_discovered=0, pages_sampled_raw=0, pages_rendered=0,
            page_roles_sampled=[], not_observed_roles=[], limitations=[error_msg], runtime_ms=0
        ),
        findings=[],
        proactive_suggestions=[]
    )
