import extruct
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import re
from src.schemas.v1.facts import StructuredFact, FactType, FactSource
from src.schemas.v1.findings import CandidateFinding
from pydantic import HttpUrl

def parse_json_ld_facts(html_content: str, url: str) -> List[StructuredFact]:
    data = extruct.extract(html_content, syntaxes=['json-ld'])
    json_ld_data = data.get('json-ld', [])
    
    facts = []
    for item in json_ld_data:
        item_type = item.get('@type', '')
        if item_type == 'Product':
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
    return facts

def extract_html_text(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'lxml')
    texts = []
    for tag in ['main', 'article', 'h1', 'footer']:
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

def check_js_rendering_gap(raw_html: str, rendered_html: str, raw_facts: List[StructuredFact], url: str) -> List[CandidateFinding]:
    """ E-01: JS Rendering Gap 
    When core page-role facts appear after render but have no raw/noscript equivalent.
    """
    rendered_facts = extract_facts_from_html(rendered_html, url, source="rendered_only")
    findings = []
    
    for r_fact in rendered_facts:
        if r_fact.fact_type in ['price', 'article_title']:
            # Check if this fact is missing in raw facts
            if not any(f.value == r_fact.value for f in raw_facts if f.fact_type == r_fact.fact_type):
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
