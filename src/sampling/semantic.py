import re
from typing import Dict, List, Set, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import json

def get_template_signature(html: str) -> str:
    if not html: return ""
    soup = BeautifulSoup(html, 'lxml')
    tags = [tag.name for tag in soup.find_all(['header', 'footer', 'nav', 'main', 'article', 'aside', 'section', 'form'])]
    return "-".join(tags)

def extract_json_ld_types(html: str) -> list:
    if not html: return []
    soup = BeautifulSoup(html, 'lxml')
    types = []
    for script in soup.find_all('script', type='application/ld+json'):
        if not script.string: continue
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and '@type' in data:
                types.append(str(data['@type']).lower())
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and '@type' in item:
                        types.append(str(item['@type']).lower())
        except Exception:
            continue
    return types

def infer_role_multi_signal(url: str, html: str, anchor_text: str = "") -> str:
    scores = {"landing": 0.0, "detail": 0.0, "editorial": 0.0, "contact": 0.0, "index": 0.0}
    path = urlparse(url).path.lower()
    
    if not path or path == "/": scores["landing"] += 5.0
    else:
        if re.search(r'(blog|news|article|insights)', path): scores["editorial"] += 1.0
        if re.search(r'(contact|about)', path): scores["contact"] += 2.0
        if re.search(r'(product|item|p/|service|solution)', path): scores["detail"] += 1.0
            
    anchor = anchor_text.lower()
    if "blog" in anchor or "news" in anchor: scores["editorial"] += 1.0
    if "contact" in anchor or "about us" in anchor: scores["contact"] += 2.0
    if "buy" in anchor or "shop" in anchor or "price" in anchor: scores["detail"] += 2.0
        
    if html:
        ld_types = extract_json_ld_types(html)
        if 'product' in ld_types or 'offer' in ld_types or 'softwareapplication' in ld_types: scores["detail"] += 5.0
        if 'article' in ld_types or 'newsarticle' in ld_types or 'blogposting' in ld_types: scores["editorial"] += 5.0
        if 'organization' in ld_types or 'localbusiness' in ld_types: scores["contact"] += 3.0
            
        soup = BeautifulSoup(html, 'lxml')
        h1 = soup.find('h1')
        title = soup.title.string if soup.title else ""
        text_sig = f"{h1.text if h1 else ''} {title}".lower()
        if "contact" in text_sig or "about" in text_sig: scores["contact"] += 3.0
        if soup.find(class_=re.compile(r'(price|add-to-cart|buy|product)', re.I)): scores["detail"] += 2.0
        if soup.find('article'): scores["editorial"] += 2.0
        if soup.find('form') and ("contact" in text_sig or "login" in text_sig): scores["contact"] += 2.0

    best_role = max(scores, key=scores.get)
    if scores[best_role] == 0: return "unknown"
    return best_role
