from typing import Literal, List, Dict, Any, Optional
from pydantic import BaseModel, HttpUrl

ConfidenceLevel = Literal["low", "medium", "high"]
SeverityLevel = Literal["critical", "high", "medium", "low"]
CategoryType = Literal["discoverability", "engagement", "content-extractability"]

class CandidateFinding(BaseModel):
    detector_id: str
    mechanism: str
    confidence: ConfidenceLevel
    affected_entity: str
    evidence_items: List[Dict[str, Any]]
    category: CategoryType
    page_urls: List[HttpUrl]

class SuggestedAction(BaseModel):
    summary: str
    priority: SeverityLevel
    mechanism: Optional[str] = None
    verification: Optional[str] = None

class FinalFinding(BaseModel):
    id: str
    title: str
    severity: SeverityLevel
    evidence: str
    suggested_action: SuggestedAction
    evidence_items: Optional[List[Dict[str, Any]]] = None # Included for report completeness, optional in schema
    affected_urls: Optional[List[HttpUrl]] = None
    category: Optional[CategoryType] = None
    confidence: Optional[ConfidenceLevel] = None
    why_it_matters: Optional[str] = None
    detector_id: Optional[str] = None
