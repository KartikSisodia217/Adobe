from typing import List
from src.schemas.v1 import CandidateFinding

def normalize_findings(findings: List[CandidateFinding]) -> List[CandidateFinding]:
    for f in findings:
        f.mechanism = " ".join(f.mechanism.lower().split())
        f.affected_entity = " ".join(f.affected_entity.lower().split())
        
        # Normalize evidence items
        for ev in f.evidence_items:
            if "description" not in ev:
                ev["description"] = "Evidence item"
    return findings
