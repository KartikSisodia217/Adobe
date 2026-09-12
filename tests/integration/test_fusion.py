import pytest
from src.schemas.v1 import CandidateFinding
from src.fusion.dedupe import deduplicate_findings
from src.fusion.scoring import assign_severity_and_confidence
from src.fusion.cap import cap_findings
from src.reporting.report_builder import build_report

def test_fusion_does_not_invent_evidence():
    findings = [
        CandidateFinding(
            detector_id="D-01", mechanism="retrieval access restriction", confidence="high",
            affected_entity="bot", evidence_items=[{"description": "robots"}],
            category="discoverability", page_urls=["http://example.com"]
        )
    ]
    scored = assign_severity_and_confidence(findings)
    final, pro = cap_findings(scored)
    assert len(final) == 1
    assert final[0].severity == "critical" # Because of string match in stub
    assert final[0].evidence == "Detector flagged retrieval access restriction on bot."

def test_fusion_suppresses_low_confidence():
    findings = [
        CandidateFinding(
            detector_id="D-02", mechanism="minor flaw", confidence="low",
            affected_entity="page", evidence_items=[{"description": "low ev"}],
            category="discoverability", page_urls=["http://example.com"]
        )
    ]
    scored = assign_severity_and_confidence(findings)
    final, pro = cap_findings(scored)
    assert len(final) == 0

def test_fusion_dedupes_same_mechanism():
    findings = [
        CandidateFinding(
            detector_id="E-01", mechanism="render gap", confidence="medium",
            affected_entity="price", evidence_items=[{"description": "e1"}],
            category="content-extractability", page_urls=["http://example.com"]
        ),
        CandidateFinding(
            detector_id="E-01", mechanism="render gap", confidence="medium",
            affected_entity="price", evidence_items=[{"description": "e2"}],
            category="content-extractability", page_urls=["http://example.com"]
        )
    ]
    deduped = deduplicate_findings(findings)
    assert len(deduped) == 1
    assert len(deduped[0].evidence_items) == 2
