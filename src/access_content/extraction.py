import json
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Tuple
import re
from src.schemas.v1.facts import StructuredFact, FactType, FactSource
from src.schemas.v1.findings import CandidateFinding
from pydantic import HttpUrl

def parse_json_ld_facts(html_content: str, url: str) -> Tuple[List[StructuredFact], List[CandidateFinding]]:
    soup = BeautifulSoup(html_content, 'lxml')
    facts = []
    proactive_findings = []
    
    json_ld_items = []
    for script in soup.find_all('script', type='application/ld+json'):
        if script.string:
            try:
                data = json.loads(script.string.strip())
                if isinstance(data, list):
                    json_ld_items.extend(data)
                elif isinstance(data, dict):
                    json_ld_items.append(data)
            except Exception:
                continue
                
    for item in json_ld_items:
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
                
            product_name = str(item.get('name', 'Unknown'))
            if 'name' in item:
                facts.append(StructuredFact(fact_type="product_name", value=product_name, source="json_ld", page_url=HttpUrl(url)))
            if 'offers' in item:
                offers = item['offers']
                if isinstance(offers, dict):
                    if 'price' in offers:
                        try:
                            val = str(float(offers['price']))
                            currency = str(offers.get('priceCurrency', 'Unknown')).lower()
                            facts.append(StructuredFact(
                                fact_type="price", 
                                value=val, 
                                source="json_ld", 
                                page_url=HttpUrl(url),
                                currency=currency,
                                entity=product_name
                            ))
                        except ValueError:
                            pass
                    if 'priceValidUntil' in offers:
                        facts.append(StructuredFact(
                            fact_type="availability",
                            value=f"Valid until {offers['priceValidUntil']}",
                            source="json_ld",
                            page_url=HttpUrl(url)
                        ))
                    if 'availability' in offers:
                        avail = str(offers['availability'])
                        if 'InStock' in avail:
                            facts.append(StructuredFact(fact_type="availability", value="In stock", source="json_ld", page_url=HttpUrl(url)))
        elif item_type == 'Article' or item_type == 'NewsArticle':
            if 'headline' in item:
                facts.append(StructuredFact(fact_type="article_title", value=str(item['headline']), source="json_ld", page_url=HttpUrl(url)))
        elif item_type == 'Organization':
            if 'sameAs' not in item:
                proactive_findings.append(CandidateFinding(
                    detector_id="P-02",
                    mechanism="entity authority and citation resilience",
                    confidence="high",
                    affected_entity="Organization Schema",
                    evidence_items=[{"missing_property": "sameAs", "description": "No authoritative external corroboration linked."}],
                    category="discoverability",
                    page_urls=[HttpUrl(url)]
                ))
            if 'name' in item:
                facts.append(StructuredFact(fact_type="organization_name", value=str(item['name']), source="json_ld", page_url=HttpUrl(url)))
                
    return facts, proactive_findings

def extract_html_text(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'lxml')
    
    # HTML Noise Filter: ignore non-content blocks
    for tag in soup(['nav', 'aside', 'script', 'style', 'header']):
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
            
    # Extract prices with currency and optional billing period context
    text = extract_html_text(html_content)
    # Using a cleaner regex string for currencies
    price_pattern = r'(\$|€|£|¥|₹|usd\s?|eur\s?|gbp\s?|jpy\s?|inr\s?)\s?(\d+(?:[.,]\d{1,2})?)(?:\s*(/month|/year|per month|per year|billed annually|billed monthly))?'
    price_matches = re.finditer(price_pattern, text, re.IGNORECASE)
    
    h1_text = h1s[0].get_text(strip=True) if h1s else "Unknown"
    
    for match in price_matches:
        try:
            currency_raw = match.group(1).strip().lower()
            val = str(float(match.group(2).replace(',', '.')))
            period_raw = (match.group(3) or "").strip().lower()
            
            # Normalize period
            period = "one-time"
            if "month" in period_raw:
                period = "monthly"
            elif "year" in period_raw or "annual" in period_raw:
                period = "yearly"
                
            # Normalize currency
            currency_map = {"$": "usd", "€": "eur", "£": "gbp", "¥": "jpy", "₹": "inr"}
            currency = currency_map.get(currency_raw, currency_raw)
                
            facts.append(StructuredFact(
                fact_type="price", 
                value=val, 
                source=source, 
                page_url=HttpUrl(url),
                currency=currency,
                billing_period=period,
                entity=h1_text
            ))
        except ValueError:
            pass
            
    return facts

def check_schema_contradiction(raw_facts: List[StructuredFact], url: str) -> List[CandidateFinding]:
    """ D-02: Schema Contradiction (Entity-Aware) """
    findings = []
    prices = [f for f in raw_facts if f.fact_type == 'price']
    
    # Compare raw_html prices vs json_ld prices using entity attributes
    raw_entities = set([(f.entity, f.value, f.currency, f.billing_period) for f in prices if f.source in ['raw_html', 'noscript']])
    json_ld_entities = set([(f.entity, f.value, f.currency, f.billing_period) for f in prices if f.source == 'json_ld'])
    
    if raw_entities and json_ld_entities:
        unsupported_json_ld = []
        for j_ent, j_val, j_curr, j_per in json_ld_entities:
            # We only claim a contradiction if the JSON-LD price explicitly conflicts 
            # with a visible price of the same entity, currency, and billing period.
            has_matching_context = False
            has_exact_match = False
            
            for r_ent, r_val, r_curr, r_per in raw_entities:
                ent_match = (j_ent.lower() == r_ent.lower()) or (j_ent.lower() == 'unknown') or (r_ent.lower() == 'unknown')
                curr_match = (j_curr.lower() == r_curr.lower()) or (j_curr.lower() == 'unknown') or (r_curr.lower() == 'unknown')
                per_match = (j_per.lower() == r_per.lower()) or (j_per.lower() == 'unknown') or (r_per.lower() == 'unknown')
                
                if ent_match and curr_match and per_match:
                    has_matching_context = True
                    if r_val == j_val:
                        has_exact_match = True
                        
            # It's only a true contradiction if we found a visible price with the same context
            # but the numerical value was different. If it's a completely different product,
            # billing period or currency, it's just an alternative variant, not a contradiction.
            if has_matching_context and not has_exact_match:
                unsupported_json_ld.append((j_ent, j_val, j_curr, j_per))
                
        if unsupported_json_ld and len(unsupported_json_ld) == len(json_ld_entities):
            findings.append(CandidateFinding(
                detector_id="D-02",
                mechanism="contradictory facts",
                confidence="high",
                affected_entity="Structured Data",
                evidence_items=[{
                    "visible_price_entities": [{"entity": e, "value": v, "currency": c, "period": p} for e, v, c, p in raw_entities],
                    "json_ld_price_entities": [{"entity": e, "value": v, "currency": c, "period": p} for e, v, c, p in json_ld_entities]
                }],
                category="discoverability",
                page_urls=[HttpUrl(url)]
            ))
            
    return findings

import difflib

def token_set_ratio(s1: str, s2: str) -> int:
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    
    intersection = tokens1.intersection(tokens2)
    diff1to2 = tokens1 - tokens2
    diff2to1 = tokens2 - tokens1
    
    t0 = " ".join(sorted(intersection))
    t1 = " ".join(sorted(intersection.union(diff1to2)))
    t2 = " ".join(sorted(intersection.union(diff2to1)))
    
    def ratio(a, b):
        if not a or not b: return 0
        return int(difflib.SequenceMatcher(None, a, b).ratio() * 100)
    
    if not t0 and not t1 and not t2: return 0
    return max(ratio(t0, t1), ratio(t0, t2), ratio(t1, t2))

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
            similarity = token_set_ratio(r_fact.value.lower(), f.value.lower())
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
        parent = img.find_parent(['main', 'article', 'figure'])
        
        # Check if the image looks like it contains primary factual content (charts, infographics, product stats)
        img_src = img.get('src', '').lower()
        img_class = ' '.join(img.get('class', [])).lower()
        
        is_factual = any(kw in img_src or kw in img_class for kw in ['chart', 'graph', 'data', 'stat', 'infographic', 'price'])
        
        if parent and is_factual and not img.get('alt'):
            findings.append(CandidateFinding(
                detector_id="E-02",
                mechanism="unreadable non-text factual content",
                confidence="medium",
                affected_entity="Data/Chart Image",
                evidence_items=[{"img_src": img.get('src'), "reason": "Image appears to contain factual data but lacks machine-readable alt text."}],
                category="content-extractability",
                page_urls=[HttpUrl(url)]
            ))
            break # only 1 needed per page
    return findings
