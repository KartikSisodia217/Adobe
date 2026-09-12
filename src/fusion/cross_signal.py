from typing import List
from src.schemas.v1 import CandidateFinding, AuditContext

def cross_validate_findings(findings: List[CandidateFinding], context: AuditContext) -> List[CandidateFinding]:
    """
    Applies multi-variate reasoning across independent signals.
    E.g. If rendering gap occurs on >50% of sampled pages, elevate confidence.
    """
    processed = []
    
    # 1. Site-wide Rendering Gap correlation
    rendering_gaps = [f for f in findings if f.detector_id == "E-01"]
    if len(rendering_gaps) > 0 and len(context.raw_pages) > 0:
        ratio = len(rendering_gaps) / max(1, len(context.raw_pages))
        if ratio >= 0.5:
            # Upgrade all to site-wide confidence
            for gap in rendering_gaps:
                gap.confidence = "high"
                gap.evidence_items.append({"cross_signal": "Occurs on >= 50% of site pages"})
                
    # 2. Correlate JSON-LD contradictions with rendering gaps
    contradictions = [f for f in findings if f.detector_id == "D-02"]
    for gap in rendering_gaps:
        related = [c for c in contradictions if c.page_urls[0] == gap.page_urls[0]]
        if related:
            gap.confidence = "high"
            gap.evidence_items.append({"cross_signal": "Correlated with JSON-LD contradiction on same page"})

    for f in findings:
        processed.append(f)
        
    return processed
