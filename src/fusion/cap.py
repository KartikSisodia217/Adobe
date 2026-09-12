from typing import List, Tuple
from src.schemas.v1 import CandidateFinding, ProactiveSuggestion, FinalFinding, SuggestedAction

def get_suggested_action(finding: CandidateFinding) -> SuggestedAction:
    if finding.detector_id == "D-01":
        return SuggestedAction(summary="This crawler is blocked. If AI discoverability is a goal, review whether public content should be accessible to it.", priority="high")
    if finding.detector_id == "E-01":
        return SuggestedAction(summary="Move core facts (like pricing or availability) out of client-side JavaScript and render them in the static HTML.", priority="high", mechanism="Server-Side Rendering (SSR) or Static Site Generation (SSG)")
    if finding.detector_id == "E-02":
        return SuggestedAction(summary="Provide machine-readable text alternatives (alt text or structured data) for images containing primary factual content.", priority="medium")
    if finding.detector_id == "D-02":
        return SuggestedAction(summary="Ensure your JSON-LD structured data matches the visible text on the page.", priority="high")
    if finding.detector_id == "G-02":
        return SuggestedAction(summary="Ensure all modal overlays can be closed safely using the 'Escape' key or standard button clicks without trapping focus.", priority="critical")
    if finding.detector_id == "P-01":
        return SuggestedAction(summary="Inject missing properties into your JSON-LD Product schema.", priority="medium", verification='<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "Product",\n  "description": "Add product description here",\n  "image": "https://example.com/image.jpg",\n  "sku": "12345"\n}\n</script>')
    if finding.detector_id == "P-02":
        return SuggestedAction(summary="Review authoritative entity references and add sameAs only after exact identity verification.", priority="medium", verification='<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "Organization",\n  "name": "Your Brand",\n  "sameAs": ["https://www.wikidata.org/wiki/YOUR_EXACT_QID"]\n}\n</script>')

    return SuggestedAction(
        summary=f"Address {finding.mechanism} on {finding.affected_entity}",
        priority="high"
    )

def cap_findings(scored: List[dict]) -> Tuple[List[FinalFinding], List[ProactiveSuggestion], dict]:
    # Sort by severity rank desc, detector_id asc, affected_entity asc
    sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    scored.sort(key=lambda x: (
        -sev_rank[x["severity"]], 
        x["finding"].detector_id, 
        x["finding"].affected_entity
    ))
    
    final_findings = []
    proactive = []
    
    crit_high_count = 0
    medium_count = 0
    
    # Track G-02 URLs to suppress G-03
    g02_urls = set()
    for s in scored:
        if s["finding"].detector_id == "G-02":
            for url in s["finding"].page_urls:
                g02_urls.add(str(url))
    
    for idx, s in enumerate(scored):
        f = s["finding"]
        sev = s["severity"]
        
        # Handle Proactive Suggestions
        if f.detector_id.startswith("P-"):
            if len(proactive) < 3:
                proactive.append(ProactiveSuggestion(
                    id=f"P-{(len(proactive)+1):03d}",
                    detector_id=f.detector_id,
                    title=f.mechanism.capitalize(),
                    priority="medium",
                    rationale=f"Found {len(f.evidence_items)} optimization opportunities for {f.affected_entity}."
                ))
            continue
            
        # Suppress G-03 if G-02 fired on the same URL
        if f.detector_id == "G-03":
            if any(str(url) in g02_urls for url in f.page_urls):
                continue
        
        if sev in ("critical", "high"):
            crit_high_count += 1
            include = True
        elif sev == "medium":
            if len(final_findings) < 8 and medium_count < 3:
                medium_count += 1
                include = True
            else:
                include = False
        else:
            include = False
            
        if include and len(final_findings) < 8:
            # Generate a rich, context-aware evidence string
            evidence_details = []
            for item in f.evidence_items[:3]: # show up to 3 context clues
                if "bot" in item:
                    evidence_details.append(f"Bot '{item['bot']}' is explicitly disallowed.")
                elif "missing_fact" in item:
                    evidence_details.append(f"Fact '{item['missing_fact']}' is missing in raw HTML.")
                elif "route_name" in item:
                    evidence_details.append(f"Route '{item['route_name']}' is inaccessible via standard navigation.")
                elif "escape_failed" in item:
                    evidence_details.append("Modal overlay could not be dismissed safely.")
                elif "value" in item and "fact_type" in item:
                    evidence_details.append(f"Conflicting value '{item['value']}' found for {item['fact_type']}.")
            
            if evidence_details:
                evidence_str = f"Detector flagged {f.mechanism}: " + " ".join(evidence_details)
            else:
                evidence_str = f"Detector flagged {f.mechanism} on {f.affected_entity}."
                
            if len(evidence_str) > 500:
                evidence_str = evidence_str[:497] + "..."
                
            ff = FinalFinding(
                id=f"F-{(len(final_findings)+1):03d}",
                title=f"{f.mechanism.capitalize()}",
                severity=sev,
                evidence=evidence_str,
                evidence_items=f.evidence_items,
                affected_urls=f.page_urls,
                category=f.category,
                confidence=f.confidence,
                detector_id=f.detector_id,
                suggested_action=get_suggested_action(f)
            )
            final_findings.append(ff)
            
    total_detected = sum(1 for x in scored if not x["finding"].detector_id.startswith("P-"))
    suppressed = total_detected - len(final_findings)
            
    return final_findings, proactive, {"total_detected": total_detected, "suppressed": max(0, suppressed)}
