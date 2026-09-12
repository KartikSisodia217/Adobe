from typing import List
from src.schemas.v1 import CandidateFinding

def assign_severity_and_confidence(findings: List[CandidateFinding]) -> List[dict]:
    scored = []
    
    for f in findings:
        conf = f.confidence
        # Evidence volume increases confidence
        if len(f.evidence_items) > 1 and conf == "low":
            conf = "medium"
            
        # Severity is based on Impact × Scope × Mechanism (independent of confidence)
        mech = f.mechanism.lower()
        if "retrieval access restriction" in mech or "modal focus trap" in mech:
            # Complete blocker for AI retrieval or user engagement
            severity = "critical"
        elif "rendering gap" in mech or "primary-route-unreachable" in mech:
            # Significant barrier to core fact extraction or navigation
            severity = "high"
        elif "schema validation" in mech or "contradictory facts" in mech:
            # Misinformation / Disambiguation issue
            severity = "medium"
        elif "unnamed-essential-control" in mech or "non-text trap" in mech:
            severity = "low"
        else:
            severity = "medium"
            
        # Suppress extremely weak signals
        if conf == "low" and len(f.evidence_items) <= 1:
            continue
            
        scored.append({
            "finding": f,
            "confidence": conf,
            "severity": severity
        })
        
    return scored
