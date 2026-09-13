from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from .findings import FinalFinding

class Summary(BaseModel):
    total_detected: int = 0
    reported_top_findings: int = 0
    suppressed_findings: int = 0
    total_findings: int # Kept for backwards compatibility
    critical: int
    high: int
    medium: int
    low: int
    proactive_suggestions: int
    narrative: Optional[str] = None
    scores: Dict[str, int] = Field(default_factory=dict)

class ExternalCalls(BaseModel):
    wikidata: int = 0

class Coverage(BaseModel):
    pages_discovered: int
    pages_sampled_raw: int
    pages_rendered: int
    page_roles_sampled: List[str]
    not_observed_roles: List[str]
    limitations: List[str]
    runtime_ms: int
    external_calls: ExternalCalls = Field(default_factory=ExternalCalls)

class ProactiveSuggestion(BaseModel):
    id: str
    detector_id: Optional[str] = None
    title: str
    priority: Literal["high", "medium", "low"]
    rationale: str

class AuditReport(BaseModel):
    site: str
    audited_at: str
    audit_version: str
    summary: Summary
    coverage: Coverage
    findings: List[FinalFinding]
    proactive_suggestions: List[ProactiveSuggestion]
    query_simulation: List[Dict] = Field(default_factory=list)
