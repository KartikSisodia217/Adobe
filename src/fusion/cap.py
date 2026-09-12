from typing import List, Tuple
from src.schemas.v1 import CandidateFinding, ProactiveSuggestion, FinalFinding, SuggestedAction

def get_suggested_action(finding: CandidateFinding) -> SuggestedAction:
    if finding.detector_id == "D-01":
        return SuggestedAction(summary="Add 'Allow: /' for AI retrieval bots like OAI-SearchBot in robots.txt.", priority="high")
    if finding.detector_id == "E-01":
        return SuggestedAction(summary="Move core facts (like pricing or availability) out of client-side JavaScript and render them in the static HTML.", priority="high", mechanism="Server-Side Rendering (SSR) or Static Site Generation (SSG)")
    if finding.detector_id == "D-02":
        return SuggestedAction(summary="Ensure your JSON-LD structured data matches the visible text on the page.", priority="high")
    if finding.detector_id == "G-02":
        return SuggestedAction(summary="Ensure all modal overlays can be closed safely using the 'Escape' key or standard button clicks without trapping focus.", priority="critical")
    if finding.detector_id == "P-01":
        return SuggestedAction(summary="Inject missing properties into your JSON-LD Product schema.", priority="medium", verification='<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "Product",\n  "description": "Add product description here",\n  "image": "https://example.com/image.jpg",\n  "sku": "12345"\n}\n</script>')

    return SuggestedAction(
        summary=f"Address {finding.mechanism} on {finding.affected_entity}",
        priority="high"
    )

def cap_findings(scored: List[dict]) -> Tuple[List[FinalFinding], List[ProactiveSuggestion]]:
    # Sort by severity rank desc, detector_id asc, affected_entity asc
    sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    scored.sort(key=lambda x: (
        -sev_rank[x["severity"]], 
        x["finding"].detector_id, 
        x["finding"].affected_entity
    ))
    
    final_findings = []
    proactive = []
    
    crit_high_count = 0
    medium_count = 0
    
    for idx, s in enumerate(scored):
        f = s["finding"]
        sev = s["severity"]
        
        # Handle Proactive Suggestions
        if f.detector_id.startswith("P-"):
            if len(proactive) < 3:
                proactive.append(ProactiveSuggestion(
                    id=f"P-{(len(proactive)+1):03d}",
                    title=f.mechanism.capitalize(),
                    priority="medium",
                    rationale=f"Found {len(f.evidence_items)} optimization opportunities for {f.affected_entity}."
                ))
            continue
        
        if sev in ("critical", "high"):
            crit_high_count += 1
            include = True
        elif sev == "medium":
            if len(final_findings) < 8 and medium_count < 3:
                medium_count += 1
                include = True
            else:
                include = False
        else:
            include = False
            
        if include and len(final_findings) < 8:
            evidence_str = f"Found {len(f.evidence_items)} issues relating to {f.mechanism}."
            if len(evidence_str) > 500:
                evidence_str = evidence_str[:497] + "..."
                
            ff = FinalFinding(
                id=f"F-{(len(final_findings)+1):03d}",
                title=f"{f.mechanism.capitalize()}",
                severity=sev,
                evidence=evidence_str,
                suggested_action=get_suggested_action(f)
            )
            final_findings.append(ff)
            
    return final_findings, proactive
