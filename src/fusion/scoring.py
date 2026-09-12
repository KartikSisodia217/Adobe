from typing import List
from src.schemas.v1 import CandidateFinding

def assign_severity_and_confidence(findings: List[CandidateFinding]) -> List[dict]:
    scored = []
    
    for f in findings:
        conf = f.confidence
        if len(f.evidence_items) > 1 and conf == "low":
            conf = "medium"
            
        severity = "low"
        if conf == "high":
            if f.detector_id == "G-02":
                severity = "critical"
            elif f.detector_id in ("D-01", "D-02", "E-01", "F-02"):
                severity = "high"
            else:
                severity = "high"
        elif conf == "medium":
            severity = "medium"
            
        if conf == "low" and len(f.evidence_items) <= 1:
            continue
            
        scored.append({
            "finding": f,
            "confidence": conf,
            "severity": severity
        })
        
    return scored
