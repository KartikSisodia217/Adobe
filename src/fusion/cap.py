from typing import List, Tuple
from src.schemas.v1 import CandidateFinding, ProactiveSuggestion, FinalFinding, SuggestedAction

def get_suggested_action(finding: CandidateFinding) -> SuggestedAction:
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
            
    # Proactive stubs (for demo if none generated)
    # The actual implementation would pull from specific proactive candidate objects.
    
    return final_findings, proactive
