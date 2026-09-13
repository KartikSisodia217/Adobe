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
    
    if "blog" in anchor or "news" in anchor or re.search(r'(blog|news|article|insights|update|press)', path):
        if len(path.split("/")) > 2 or "-" in path.split("/")[-1]:
            return "editorial"
        return "index"
        
    if re.search(r'(contact|about|team|help|support|faq)', anchor) or re.search(r'(contact|about|team|help|support|faq)', path):
        return "contact"
        
    if "price" in anchor or "pricing" in anchor or "plan" in anchor or "pricing" in path:
        return "detail"
        
    if re.search(r'(product|item|p/|service|solution|feature|docs|course|event|menu)', path) or re.search(r'(buy|shop|register|book|menu)', anchor):
        return "detail"
        
    if path.endswith("s") or path.endswith("s/") or "all" in anchor or "browse" in anchor or re.search(r'(category|collections|list)', path):
        return "index"
        
    if "-" in path.split("/")[-1] or re.search(r'\d+', path.split("/")[-1]):
        return "detail"
        
    return "unknown"

def select_raw_candidates(homepage_url: str, discovered_urls: set, sitemap_urls: list, max_raw_cap: int = 15) -> List[Dict]:
    """Phase 1: Select URLs for fast raw fetching based on heuristics (URL patterns)."""
    all_candidates = list(discovered_urls.union(set(sitemap_urls)))
    scored = []
    role_counts = {"landing": 1, "detail": 0, "editorial": 0, "contact": 0, "index": 0, "unknown": 0}
    
    for url in all_candidates[:500]:
        if url == homepage_url:
            continue
        role = infer_role(url)
        score = 20 if role_counts.get(role, 0) == 0 else max(1, 10 - role_counts.get(role, 0))
        scored.append({"url": url, "role": role, "score": score})
        role_counts[role] = role_counts.get(role, 0) + 1
        
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    raw_candidates = [{"url": homepage_url, "role": "landing"}]
    for cand in scored[:(max_raw_cap - 1)]:
        raw_candidates.append(cand)
        
    return raw_candidates

def select_render_candidates(raw_pages: List[RawPage], max_render_cap: int = 5) -> List[RawPage]:
    """Phase 2: Select URLs for expensive browser rendering based on accurate DOM semantics."""
    render_cands = []
    seen_roles = set()
    
    # Always include landing
    landing = next((p for p in raw_pages if p.page_role == "landing"), None)
    if landing:
        render_cands.append(landing)
        seen_roles.add("landing")
        
    # Prioritize semantic diversity
    for page in raw_pages:
        if len(render_cands) >= max_render_cap:
            break
        if page.page_role not in seen_roles and page.status_code == 200:
            render_cands.append(page)
            seen_roles.add(page.page_role)
            
    # Fill remaining slots with priority roles if diversity didn't fill it
    priority_roles = ["detail", "index", "editorial", "unknown"]
    for pr in priority_roles:
        for page in raw_pages:
            if len(render_cands) >= max_render_cap:
                break
            if page.page_role == pr and page not in render_cands and page.status_code == 200:
                render_cands.append(page)
                
    return render_cands

from bs4 import BeautifulSoup
import json

def refine_page_roles(raw_pages: List[RawPage]) -> None:
    """Semantically infer page roles using actual DOM content (Schema, H1, Title, OpenGraph, Breadcrumbs, Structure)."""
    for page in raw_pages:
        if page.page_role == "landing" or not page.html_content:
            continue
            
        soup = BeautifulSoup(page.html_content, 'lxml')
        title = (soup.title.string or "").lower()
        h1s = " ".join([h.get_text() for h in soup.find_all('h1')]).lower()
        
        is_product = False
        is_article = False
        is_contact = False
        is_index = False
        
        # 1. Strongest signal: JSON-LD Schema
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    doc_type = data.get('@type', '').lower()
                    if 'product' in doc_type or 'offer' in doc_type:
                        is_product = True
                    elif 'article' in doc_type or 'news' in doc_type or 'blogposting' in doc_type:
                        is_article = True
                    elif 'contactpage' in doc_type or 'organization' in doc_type:
                        is_contact = True
                    elif 'collectionpage' in doc_type or 'itemlist' in doc_type:
                        is_index = True
            except Exception:
                pass
                
        # 2. OpenGraph Meta Tags
        og_type = soup.find('meta', property='og:type')
        if og_type and og_type.get('content'):
            ctype = og_type.get('content').lower()
            if ctype in ('product', 'og:product'): is_product = True
            elif ctype in ('article', 'og:article'): is_article = True
            
        # 3. Breadcrumbs & CTA Semantics
        nav_text = " ".join([nav.get_text() for nav in soup.find_all(['nav', 'div', 'ul'], class_=re.compile(r'breadcrumb|nav|menu', re.I))]).lower()
        cta_text = " ".join([a.get_text() for a in soup.find_all(['a', 'button', 'input'], class_=re.compile(r'btn|button|cta|submit', re.I))]).lower()
        if re.search(r'(add to cart|buy now|checkout|register|book|enroll|get started)', cta_text):
            is_product = True
            
        # 4. Structural patterns (Link density & Repeated Cards)
        # If there are many identical card-like elements, it's likely an index/listing page
        cards = soup.find_all(class_=re.compile(r'card|item|grid|list|row|col', re.I))
        if len(cards) > 6 and not is_product and not is_article:
            is_index = True
            
        # 5. Semantic text signals
        if re.search(r'(contact us|get in touch|support|help|faq)', title) or re.search(r'(get in touch|support|help|faq)', h1s):
            is_contact = True
        elif re.search(r'(blog|news|article|update)', title) or 'read more' in nav_text:
            is_article = True
        elif 'price' in title or 'shop' in title or 'docs' in title:
            is_product = True
            
        # Apply semantic roles
        if is_product:
            page.page_role = "detail"
        elif is_article:
            page.page_role = "editorial"
        elif is_contact:
            page.page_role = "contact"
        elif is_index:
            page.page_role = "index"
