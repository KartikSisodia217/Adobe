from typing import List
from src.schemas.v1 import CandidateFinding

def deduplicate_findings(findings: List[CandidateFinding]) -> List[CandidateFinding]:
    merged = {}
    
    for f in findings:
        # Simple canonical URL clustering (using first page_url)
        cluster = str(f.page_urls[0]) if f.page_urls else "global"
        key = (f.mechanism, f.affected_entity, cluster)
        
        if key not in merged:
            merged[key] = f
        else:
            # Keep highest confidence
            existing = merged[key]
            conf_ranks = {"low": 1, "medium": 2, "high": 3}
            if conf_ranks[f.confidence] > conf_ranks[existing.confidence]:
                f.evidence_items.extend(existing.evidence_items)
                merged[key] = f
            else:
                existing.evidence_items.extend(f.evidence_items)
                
    return list(merged.values())
