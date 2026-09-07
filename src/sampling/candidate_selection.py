from typing import List, Dict
from src.schemas.v1 import PageRole, RawPage
import re

def infer_role(url: str, in_link_count: int) -> PageRole:
    path = url.split("://")[-1].split("/", 1)[-1].lower() if "/" in url.split("://")[-1] else ""
    path = path.split("?")[0]
    
    if not path or path == "/":
        return "landing"
        
    if re.search(r'(blog|news|article|insights)', path):
        if len(path.split("/")) > 2 or "-" in path.split("/")[-1]:
            return "editorial"
        return "index"
        
    if re.search(r'(contact|about)', path):
        return "contact"
        
    if re.search(r'(product|item|p/)', path) or "-" in path.split("/")[-1]:
        return "detail"
        
    if path.endswith("s") or path.endswith("s/"): # heuristics for listings like /products
        return "index"
        
    return "unknown"

def select_candidates(homepage_raw: RawPage, discovered_urls: set, sitemap_urls: list) -> tuple[List[Dict], List[Dict]]:
    # Merge and deduplicate
    all_candidates = list(discovered_urls.union(set(sitemap_urls)))
    
    # Heuristic scoring
    scored = []
    role_counts = {"landing": 1, "detail": 0, "editorial": 0, "contact": 0, "index": 0, "unknown": 0}
    
    for url in all_candidates[:500]: # Cap to 500 to bound processing time
        if url == str(homepage_raw.url):
            continue
        role = infer_role(url, 1)
        score = 10 if role_counts[role] == 0 else 1
        scored.append({"url": url, "role": role, "score": score})
        role_counts[role] += 1
        
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    # Cap 6 total (including homepage)
    raw_candidates = [{"url": str(homepage_raw.url), "role": "landing"}]
    for cand in scored[:5]:
        raw_candidates.append(cand)
        
    # Render candidates: max 3
    # 1. Landing
    render_candidates = [{"url": str(homepage_raw.url), "role": "landing"}]
    
    # 2. Highest scoring detail or other
    if len(raw_candidates) > 1:
        render_candidates.append(raw_candidates[1])
        
    # 3. Fallback (a role not yet rendered)
    if len(raw_candidates) > 2:
        for cand in raw_candidates[2:]:
            if cand["role"] not in [c["role"] for c in render_candidates]:
                render_candidates.append(cand)
                break
                
    if len(render_candidates) < 3 and len(raw_candidates) > 2:
        render_candidates.append(raw_candidates[2])
        
    # Strictly bound render candidates to 3
    render_candidates = render_candidates[:3]
    
    return raw_candidates, render_candidates
