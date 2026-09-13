from typing import List, Dict, Any, Tuple
from src.schemas.v1.context import AuditContext
from src.schemas.v1.facts import StructuredFact
from src.schemas.v1.findings import CandidateFinding
from .parser import evaluate_robots_txt
from .extraction import parse_json_ld_facts, extract_facts_from_html, check_schema_contradiction, check_js_rendering_gap, check_non_text_trap

def run_access_content_audit(context: AuditContext) -> Tuple[List[StructuredFact], List[CandidateFinding]]:
    all_facts = []
    all_findings = []
    
    # 1. Evaluate robots.txt
    if context.robots_txt_content:
        findings = evaluate_robots_txt(context.robots_txt_content, str(context.target_url))
        all_findings.extend(findings)
        
    # 2. Evaluate Pages
    for raw_page in context.raw_pages:
        url = str(raw_page.url)
        role = raw_page.page_role
        
        # Extract facts from JSON-LD
        json_ld_facts, proactive_findings = parse_json_ld_facts(raw_page.html_content, url)
        all_facts.extend(json_ld_facts)
        # Phase 10: Adapt Detectors to Page Role
        if role in ["detail", "landing"]:
            all_findings.extend(proactive_findings)
        
        # Extract facts from Raw HTML
        raw_html_facts = extract_facts_from_html(raw_page.html_content, url, source="raw_html")
        all_facts.extend(raw_html_facts)
        
        # Check Schema Contradictions (D-02)
        page_raw_facts = json_ld_facts + raw_html_facts
        if role in ["detail", "landing", "unknown"]:
            schema_findings = check_schema_contradiction(page_raw_facts, url)
            all_findings.extend(schema_findings)
        
        # Rendered vs Raw comparisons
        rendered_page = next((p for p in context.rendered_pages if str(p.url) == url), None)
        if rendered_page:
            # E-01 JS Rendering Gap
            js_gap_findings = check_js_rendering_gap(raw_page.html_content, rendered_page.rendered_html, page_raw_facts, url)
            all_findings.extend(js_gap_findings)
            
            # E-02 Non-Text Trap
            if role in ["detail", "editorial", "landing", "unknown"]:
                non_text_findings = check_non_text_trap(rendered_page.rendered_html, url)
                all_findings.extend(non_text_findings)
            
    return all_facts, all_findings
