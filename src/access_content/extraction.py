import extruct
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Tuple
import re
from src.schemas.v1.facts import StructuredFact, FactType, FactSource
from src.schemas.v1.findings import CandidateFinding
from pydantic import HttpUrl

def parse_json_ld_facts(html_content: str, url: str) -> Tuple[List[StructuredFact], List[CandidateFinding]]:
    # extruct robustly handles malformed JSON-LD by skipping or partially parsing it
    data = extruct.extract(html_content, syntaxes=['json-ld'])
    json_ld_data = data.get('json-ld', [])
    
    facts = []
    proactive_findings = []
    
    for item in json_ld_data:
        item_type = item.get('@type', '')
        if item_type == 'Product':
            # Proactive Schema Validation
            missing_props = [p for p in ['description', 'image', 'sku'] if p not in item]
            if missing_props:
                proactive_findings.append(CandidateFinding(
                    detector_id="P-01",
                    mechanism="schema optimization",
                    confidence="high",
                    affected_entity="Product Schema",
                    evidence_items=[{"missing_properties": missing_props}],
                    category="discoverability",
                    page_urls=[HttpUrl(url)]
                ))
                
            if 'name' in item:
                facts.append(StructuredFact(fact_type="product_name", value=str(item['name']), source="json_ld", page_url=HttpUrl(url)))
            if 'offers' in item:
                offers = item['offers']
                if isinstance(offers, dict):
                    if 'price' in offers:
                        try:
                            val = str(float(offers['price']))
                            facts.append(StructuredFact(fact_type="price", value=val, source="json_ld", page_url=HttpUrl(url)))
                        except ValueError:
                            pass
                    if 'availability' in offers:
                        avail = str(offers['availability'])
                        if 'InStock' in avail:
                            facts.append(StructuredFact(fact_type="availability", value="InStock", source="json_ld", page_url=HttpUrl(url)))
        elif item_type == 'Article' or item_type == 'NewsArticle':
            if 'headline' in item:
                facts.append(StructuredFact(fact_type="article_title", value=str(item['headline']), source="json_ld", page_url=HttpUrl(url)))
        elif item_type == 'Organization':
            if 'name' in item:
                facts.append(StructuredFact(fact_type="organization_name", value=str(item['name']), source="json_ld", page_url=HttpUrl(url)))
                
    return facts, proactive_findings

def extract_html_text(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'lxml')
    
    # HTML Noise Filter: ignore non-content blocks
    for tag in soup(['nav', 'aside', 'script', 'style', 'noscript', 'header']):
        tag.decompose()
        
    texts = []
    # Fallback logic if modern tags are missing
    targets = soup.find_all(['main', 'article'])
    if not targets:
        targets = soup.find_all('body')
        
    for el in targets:
        texts.append(el.get_text(separator=' ', strip=True))
        
    for tag in ['h1', 'footer']:
        for el in soup.find_all(tag):
            texts.append(el.get_text(separator=' ', strip=True))
            
    return ' '.join(texts).lower()

def extract_facts_from_html(html_content: str, url: str, source: FactSource) -> List[StructuredFact]:
    soup = BeautifulSoup(html_content, 'lxml')
    facts = []
    
    # Simple extraction logic based on H1 and regex for prices/contact
    h1s = soup.find_all('h1')
    for h1 in h1s:
        title = h1.get_text(strip=True)
        if title:
            # We loosely assign h1 to product_name or article_title. 
            # We'll just call it article_title for simplicity if not product.
            facts.append(StructuredFact(fact_type="article_title", value=title, source=source, page_url=HttpUrl(url)))
            
    # Extract prices
    text = extract_html_text(html_content)
    price_matches = re.findall(r'\$\s?(\d+(?:\.\d{2})?)', text)
    for match in price_matches:
        try:
            val = str(float(match))
            facts.append(StructuredFact(fact_type="price", value=val, source=source, page_url=HttpUrl(url)))
        except ValueError:
            pass
            
    return facts

def check_schema_contradiction(raw_facts: List[StructuredFact], url: str) -> List[CandidateFinding]:
    """ D-02: Schema Contradiction """
    findings = []
    prices = [f for f in raw_facts if f.fact_type == 'price']
    
    # Compare raw_html prices vs json_ld prices
    raw_prices = set([f.value for f in prices if f.source in ['raw_html', 'noscript']])
    json_ld_prices = set([f.value for f in prices if f.source == 'json_ld'])
    
    if raw_prices and json_ld_prices:
        # If there is a json-ld price that contradicts a raw price
        # Actually, let's just check if they are completely disjoint
        if not raw_prices.intersection(json_ld_prices):
            findings.append(CandidateFinding(
                detector_id="D-02",
                mechanism="schema validation",
                confidence="high",
                affected_entity="Structured Data",
                evidence_items=[{"raw_prices": list(raw_prices), "json_ld_prices": list(json_ld_prices)}],
                category="discoverability",
                page_urls=[HttpUrl(url)]
            ))
            
    return findings

from thefuzz import fuzz

def normalize_availability(value: str) -> str:
    """Normalizes availability text to a standard boolean-like state using synonym mapping."""
    val = value.lower()
    in_stock_synonyms = ['instock', 'in stock', 'available', 'available now', 'in-stock']
    out_of_stock_synonyms = ['outofstock', 'out of stock', 'unavailable', 'sold out']
    
    if any(syn in val for syn in in_stock_synonyms):
        return 'in_stock'
    if any(syn in val for syn in out_of_stock_synonyms):
        return 'out_of_stock'
    return val

def is_fact_matched(r_fact: StructuredFact, raw_facts: List[StructuredFact]) -> bool:
    """Checks if a rendered fact has a matching equivalent in the raw facts."""
    for f in raw_facts:
        if f.fact_type != r_fact.fact_type:
            continue
            
        # Price: numerical equality check (handles formatting like $49.00 vs 49.0)
        if r_fact.fact_type == 'price':
            try:
                if float(r_fact.value) == float(f.value):
                    return True
            except ValueError:
                pass
                
        # Availability: synonym matching
        elif r_fact.fact_type == 'availability':
            if normalize_availability(r_fact.value) == normalize_availability(f.value):
                return True
                
        # Text fields (titles, names): Fuzzy string matching
        else:
            # Use token_set_ratio which ignores word order and handles partial matches well
            similarity = fuzz.token_set_ratio(r_fact.value.lower(), f.value.lower())
            if similarity > 85:  # 85% similarity threshold
                return True
                
    return False

def check_js_rendering_gap(raw_html: str, rendered_html: str, raw_facts: List[StructuredFact], url: str) -> List[CandidateFinding]:
    """ E-01: JS Rendering Gap 
    When core page-role facts appear after render but have no raw/noscript equivalent.
    """
    rendered_facts = extract_facts_from_html(rendered_html, url, source="rendered_only")
    findings = []
    
    for r_fact in rendered_facts:
        if r_fact.fact_type in ['price', 'article_title', 'availability']:
            # Check if this fact is missing in raw facts using fuzzy/semantic logic
            if not is_fact_matched(r_fact, raw_facts):
                findings.append(CandidateFinding(
                    detector_id="E-01",
                    mechanism="rendering gap",
                    confidence="high",
                    affected_entity="Core Facts",
                    evidence_items=[{"missing_fact": r_fact.value, "fact_type": r_fact.fact_type}],
                    category="content-extractability",
                    page_urls=[HttpUrl(url)]
                ))
    
    return findings

def check_non_text_trap(rendered_html: str, url: str) -> List[CandidateFinding]:
    """ E-02: Non-Text Trap """
    soup = BeautifulSoup(rendered_html, 'lxml')
    findings = []
    for img in soup.find_all('img'):
        # If image has no alt text but might be important (e.g. inside main)
        parent = img.find_parent(['main', 'article'])
        if parent and not img.get('alt'):
            findings.append(CandidateFinding(
                detector_id="E-02",
                mechanism="non-text trap",
                confidence="medium",
                affected_entity="Image without alt",
                evidence_items=[{"img_src": img.get('src')}],
                category="content-extractability",
                page_urls=[HttpUrl(url)]
            ))
            break # only 1 needed per page
    return findings
