from typing import List
from src.schemas.v1 import CandidateFinding

def assign_severity_and_confidence(findings: List[CandidateFinding]) -> List[dict]:
    scored = []
    
    # Calculate a rough estimate of total pages audited (or max pages affected)
    # to determine 'scope'.
    all_urls = set()
    for f in findings:
        for u in f.page_urls:
            all_urls.add(str(u))
    total_pages = max(1, len(all_urls))
    
    for f in findings:
        conf = f.confidence
        # Evidence volume increases confidence
        if len(f.evidence_items) > 1 and conf == "low":
            conf = "medium"
            
        mech = f.mechanism.lower()
        scope_ratio = len(f.page_urls) / total_pages
        
        # Base impact
        if "retrieval" in mech or "robots" in mech or "modal focus" in mech:
            base_impact = 4 # critical
        elif "rendering gap" in mech or "primary-route-unreachable" in mech or "unreachable" in mech:
            base_impact = 3 # high
        elif "schema" in mech or "contradictory" in mech or "contradiction" in mech or "ambiguous" in mech or "expired" in mech:
            base_impact = 2 # medium
        else:
            base_impact = 1 # low
            
        # Scope modifier
        if scope_ratio >= 0.5 and total_pages > 2:
            final_impact = min(4, base_impact + 1)
        elif scope_ratio <= 0.2 and base_impact > 1 and total_pages > 2:
            final_impact = base_impact - 1
        else:
            final_impact = base_impact
            
        impact_map = {4: "critical", 3: "high", 2: "medium", 1: "low", 0: "low"}
        severity = impact_map[final_impact]
            
        # Suppress extremely weak signals
        if conf == "low" and len(f.evidence_items) <= 1:
            continue
            
        scored.append({
            "finding": f,
            "confidence": conf,
            "severity": severity
        })
        
    return scored
