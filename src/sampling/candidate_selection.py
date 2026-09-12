from typing import List, Dict
from src.schemas.v1 import PageRole, RawPage
import re

def infer_role(url: str, anchor_text: str = "") -> PageRole:
    """Infers page role semantically using URL structure and anchor text context."""
    path = url.split("://")[-1].split("/", 1)[-1].lower() if "/" in url.split("://")[-1] else ""
    path = path.split("?")[0]
    
    if not path or path == "/":
        return "landing"
        
    anchor = anchor_text.lower()
    
    # Semantic inference based on anchor and path
    if "blog" in anchor or "news" in anchor or re.search(r'(blog|news|article|insights)', path):
        if len(path.split("/")) > 2 or "-" in path.split("/")[-1]:
            return "editorial"
        return "index"
        
    if "contact" in anchor or "about us" in anchor or re.search(r'(contact|about)', path):
        return "contact"
        
    if "price" in anchor or "pricing" in anchor or "plan" in anchor or "pricing" in path:
        return "detail" # Treat pricing as detail for fact extraction
        
    if re.search(r'(product|item|p/|service|solution)', path) or "buy" in anchor or "shop" in anchor:
        return "detail"
        
    if path.endswith("s") or path.endswith("s/") or "all" in anchor or "browse" in anchor:
        return "index"
        
    # Fallback to detail if structural cues suggest a specific resource (UUID/Slug)
    if "-" in path.split("/")[-1] or re.search(r'\d+', path.split("/")[-1]):
        return "detail"
        
    return "unknown"

def select_candidates(homepage_raw: RawPage, discovered_urls: set, sitemap_urls: list) -> tuple[List[Dict], List[Dict]]:
    all_candidates = list(discovered_urls.union(set(sitemap_urls)))
    scored = []
    role_counts = {"landing": 1, "detail": 0, "editorial": 0, "contact": 0, "index": 0, "unknown": 0}
    
    for url in all_candidates[:500]:
        if url == str(homepage_raw.url):
            continue
        role = infer_role(url) # Can't pass anchor text yet without rewriting discovery
        score = 20 if role_counts.get(role, 0) == 0 else max(1, 10 - role_counts.get(role, 0))
        scored.append({"url": url, "role": role, "score": score})
        role_counts[role] = role_counts.get(role, 0) + 1
        
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    # Increase coverage intelligently: Raw Cap = 12
    raw_candidates = [{"url": str(homepage_raw.url), "role": "landing"}]
    for cand in scored[:11]:
        raw_candidates.append(cand)
        
    # Increase render coverage: Render Cap = 5 (diversity sampling)
    render_candidates = [{"url": str(homepage_raw.url), "role": "landing"}]
    for cand in raw_candidates[1:]:
        if cand["role"] not in [c["role"] for c in render_candidates]:
            render_candidates.append(cand)
        if len(render_candidates) >= 5:
            break
            
    # Fill remaining slots with high-scoring pages if diversity didn't fill it
    for cand in raw_candidates[1:]:
        if len(render_candidates) >= 5:
            break
        if cand not in render_candidates:
            render_candidates.append(cand)
            
    return raw_candidates, render_candidates
