from typing import List
from src.schemas.v1 import RawPage
from src.sampling.semantic import infer_role_multi_signal, get_template_signature

def refine_page_roles(raw_pages: List[RawPage]) -> None:
    for page in raw_pages:
        if page.html_content:
            page.page_role = infer_role_multi_signal(str(page.url), page.html_content, "")

def select_render_candidates(raw_pages: List[RawPage], max_render_cap: int = 5) -> List[RawPage]:
    refine_page_roles(raw_pages)
    
    render_cands = []
    covered_roles = set()
    covered_templates = set()
    
    signatures = {}
    for p in raw_pages:
        if p.html_content and p.status_code == 200:
            signatures[str(p.url)] = get_template_signature(p.html_content)
    
    landing = next((p for p in raw_pages if p.page_role == "landing"), None)
    if landing:
        render_cands.append(landing)
        covered_roles.add("landing")
        if str(landing.url) in signatures:
            covered_templates.add(signatures[str(landing.url)])
            
    remaining = [p for p in raw_pages if p not in render_cands and p.status_code == 200]
    
    while remaining and len(render_cands) < max_render_cap:
        best_p = None
        best_score = -1.0
        for p in remaining:
            score = 0.0
            if p.page_role not in covered_roles: score += 5.0
            sig = signatures.get(str(p.url), "")
            if sig and sig not in covered_templates: score += 3.0
            if score > best_score:
                best_score = score
                best_p = p
        
        if best_p and best_score > 0:
            render_cands.append(best_p)
            covered_roles.add(best_p.page_role)
            if str(best_p.url) in signatures:
                covered_templates.add(signatures[str(best_p.url)])
            remaining.remove(best_p)
        else:
            break
            
    for p in remaining:
        if len(render_cands) >= max_render_cap: break
        render_cands.append(p)
        
    return render_cands
