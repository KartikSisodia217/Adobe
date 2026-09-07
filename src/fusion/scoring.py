from typing import List
from src.schemas.v1 import CandidateFinding

def assign_severity_and_confidence(findings: List[CandidateFinding]) -> List[dict]:
    scored = []
    
    for f in findings:
        # Confidence rules
        conf = f.confidence
        # Example escalation based on evidence count
        if len(f.evidence_items) > 1 and conf == "low":
            conf = "medium"
            
        # Severity rules (precision first)
        severity = "low"
        if conf == "high":
            if "modal trap" in f.mechanism or "retrieval access restriction" in f.mechanism:
                severity = "critical"
            else:
                severity = "high"
        elif conf == "medium":
            severity = "medium"
            
        # Suppress single low confidence evidence findings
        if conf == "low" and len(f.evidence_items) <= 1:
            continue
            
        scored.append({
            "finding": f,
            "confidence": conf,
            "severity": severity
        })
        
    return scored
