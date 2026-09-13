from datetime import datetime, timezone
from typing import List, Dict
from src.schemas.v1 import AuditContext, FinalFinding, ProactiveSuggestion, AuditReport, Summary, Coverage, ExternalCalls

def calculate_scores(findings: List[FinalFinding], context: AuditContext | None = None) -> Dict[str, int]:
    """Deterministic 0-100 summary scores; findings remain the source of truth."""
    penalties = {"critical": 28, "high": 16, "medium": 8, "low": 3}
    groups = {
        "ai_discoverability": {"discoverability", "content-extractability", "brand-identity"},
        "content_extractability": {"content-extractability"},
        "entity_clarity": {"brand-identity"},
        "brand_identity_confidence": {"brand-identity"},
        "on_site_orientation": {"engagement", "brand-identity"},
    }
    scores = {}
    for name, categories in groups.items():
        deduction = sum(penalties[f.severity] for f in findings if f.category in categories)
        scores[name] = max(0, 100 - deduction)

    # Separate First-party Identity Confidence from Cross-web verification
    first_party_deduction = sum(
        penalties[f.severity] for f in findings
        if f.detector_id in {"B-04", "D-02"}
    )
    scores["first_party_identity_confidence"] = max(0, 100 - first_party_deduction)

    external_checked = bool(context and context.external_sources)
    if external_checked:
        cross_web_deduction = sum(
            penalties[f.severity] for f in findings
            if f.detector_id in {"B-01", "B-02", "B-03", "B-05"}
        )
        scores["cross_web_identity_confidence"] = max(0, 100 - cross_web_deduction)
        scores["source_consistency"] = max(0, 100 - cross_web_deduction)
        scores["external_conflict_risk"] = min(100, cross_web_deduction)
    else:
        # Absence of cross-web evidence is uncertainty, not proof of cross-web identity clarity.
        scores["cross_web_identity_confidence"] = 50
        scores["source_consistency"] = 50
        scores["external_conflict_risk"] = 50

    scores["overall_ai_readiness"] = round(sum(scores.values()) / len(scores))
    return scores

def generate_narrative(summary: Summary, findings: List[FinalFinding], context: AuditContext) -> str:
    if summary.total_findings == 0:
        if context.budgets_consumed.get("pages_rendered", 0) == 0:
            return "No issues were detected within the observed coverage; however, browser rendering failed for all pages, so engagement and JS-rendering findings are completely unavailable."
        return "No high-confidence issues were detected within the sampled coverage."
    
    parts = []
    if summary.critical > 0:
        parts.append(f"We found {summary.critical} critical issues that severely block AI agents from navigating or comprehending your site.")
    if summary.high > 0:
        parts.append(f"There are {summary.high} high-priority rendering gaps, conflicting destinations, or schema contradictions that prevent facts from surfacing.")
    
    if len(findings) > 0:
        top_issues = ", ".join([f.title.lower() for f in findings[:2]])
        parts.append(f"Prioritize fixing the {top_issues} to ensure AI assistants can confidently extract your pricing and product data, and smoothly route users through your key workflows.")
    
    return " ".join(parts)

def build_report(context: AuditContext, findings: List[FinalFinding], proactive: List[ProactiveSuggestion], cap_stats: dict) -> AuditReport:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        if f.severity in counts:
            counts[f.severity] += 1
            
    summary = Summary(
        total_detected=cap_stats.get("total_detected", len(findings)),
        reported_top_findings=len(findings),
        suppressed_findings=cap_stats.get("suppressed", 0),
        total_findings=len(findings),
        critical=counts["critical"],
        high=counts["high"],
        medium=counts["medium"],
        low=counts["low"],
        proactive_suggestions=len(proactive)
    )
    summary.scores = calculate_scores(findings, context)
    
    # Add generated narrative to summary
    summary.narrative = generate_narrative(summary, findings, context)
    
    roles_sampled = list(set([p.page_role for p in context.raw_pages]))
    
    coverage = Coverage(
        pages_discovered=len(context.raw_pages), # Using fetched count for simplicity here
        pages_sampled_raw=context.budgets_consumed.get("raw_pages_fetched", len(context.raw_pages)),
        pages_rendered=context.budgets_consumed.get("pages_rendered", 0),
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
        proactive_suggestions=proactive,
        query_simulation=context.query_simulation,
    )

def build_minimal_error_report(input_url: str, error_msg: str) -> AuditReport:
    # Build a minimal valid report for fatal errors
    return AuditReport(
        site=input_url,
        audited_at=datetime.now(timezone.utc).isoformat() + "Z",
        audit_version="1.0.0",
        summary=Summary(total_findings=0, critical=0, high=0, medium=0, low=0, proactive_suggestions=0, narrative="No findings were generated due to an error during the audit."),
        coverage=Coverage(
            pages_discovered=0, pages_sampled_raw=0, pages_rendered=0,
            page_roles_sampled=[], not_observed_roles=[], limitations=[error_msg], runtime_ms=0
        ),
        findings=[],
        proactive_suggestions=[]
    )
