from urllib.robotparser import RobotFileParser
from typing import List, Dict, Any, Tuple, Optional
from src.schemas.v1.findings import CandidateFinding
from pydantic import HttpUrl

def evaluate_robots_txt(robots_txt_content: Optional[str], target_url: str) -> List[CandidateFinding]:
    """
    Evaluates robots.txt content against AI bot access rules vs general crawler rules.
    Yields D-01 (Retrieval Access) finding if retrieval bots are explicitly denied.
    """
    if not robots_txt_content:
        return []
    
    rp = RobotFileParser()
    rp.parse(robots_txt_content.splitlines())
    
    # Testing against major AI retrieval bots to ensure broad generalization
    retrieval_bots = [
        "OAI-SearchBot",
        "GPTBot",
        "ClaudeBot",
        "PerplexityBot",
        "CCBot",
        "Applebot-Extended"
    ]
    
    findings = []
    
    for bot in retrieval_bots:
        if not rp.can_fetch(bot, target_url):
            findings.append(CandidateFinding(
                detector_id="D-01",
                mechanism="robots.txt",
                confidence="high",
                affected_entity="Retrieval Bot Access",
                evidence_items=[{"bot": bot, "target_url": str(target_url), "rule": "Disallow"}],
                category="discoverability",
                page_urls=[HttpUrl(target_url)]
            ))
            break
            
    return findings
