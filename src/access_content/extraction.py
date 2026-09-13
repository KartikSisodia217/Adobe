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
            except (ValueError, TypeError) as exc:
                proactive_findings.append(CandidateFinding(
                    detector_id="D-03", mechanism="malformed JSON-LD", confidence="medium",
                    affected_entity="structured data", evidence_items=[{"error": type(exc).__name__, "description": "A JSON-LD block could not be parsed."}],
                    category="discoverability", page_urls=[HttpUrl(url)]
                ))
                continue
                
    def expand(items):
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                yield from expand(item["@graph"])
            elif isinstance(item, dict):
                yield item
    for item in expand(json_ld_items):
        item_types = item.get('@type', '')
        item_types = item_types if isinstance(item_types, list) else [item_types]
        if any(kind in {'Product', 'Course'} for kind in item_types):
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
        elif any(kind in {'Article', 'NewsArticle', 'FAQPage', 'BreadcrumbList'} for kind in item_types):
            if 'headline' in item:
                facts.append(StructuredFact(fact_type="article_title", value=str(item['headline']), source="json_ld", page_url=HttpUrl(url)))
        elif any(kind in {'Organization', 'Corporation', 'LocalBusiness', 'WebSite'} for kind in item_types):
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
                facts.append(StructuredFact(
                    fact_type="organization_name", value=str(item['name']),
                    source="json_ld", page_url=HttpUrl(url),
                    entity_type="organization"
                ))
        elif any(kind == 'Person' for kind in item_types):
            # Person entities are NOT organization names — model as person_name
            # so Brand name vs Founder name is NEVER treated as a contradiction.
            if 'name' in item:
                facts.append(StructuredFact(
                    fact_type="person_name", value=str(item['name']),
                    source="json_ld", page_url=HttpUrl(url),
                    entity_type="person",
                    relationship="represented_by"
                ))
            if 'url' in item:
                facts.append(StructuredFact(fact_type="official_domain", value=str(item['url']), source="json_ld", page_url=HttpUrl(url)))
            if 'email' in item or 'telephone' in item:
                facts.append(StructuredFact(fact_type="contact", value=str(item.get('email') or item.get('telephone')), source="json_ld", page_url=HttpUrl(url)))

    canonical = soup.find('link', rel=lambda value: value and 'canonical' in value)
    if canonical and canonical.get('href'):
        canonical_url = canonical['href'].strip()
        if not canonical_url.startswith(('http://', 'https://')):
            proactive_findings.append(CandidateFinding(detector_id="D-04", mechanism="invalid canonical URL", confidence="medium",
                affected_entity="canonical URL", evidence_items=[{"canonical": canonical_url, "description": "Canonical URL is not an absolute HTTP(S) URL."}],
                category="discoverability", page_urls=[HttpUrl(url)]))
                
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
            
    # ── DOM-aware price extraction ────────────────────────────────────────────
    # Price symbols that indicate struck-through / was-price nodes
    _STRIKETHROUGH_TAGS = {"s", "del", "strike"}
    _PROMO_WORDS = re.compile(r"\b(was|originally|save|discount|off|regular price|list price)\b", re.I)
    _PERIOD_RE = re.compile(r"(month|year|annual)", re.I)
    _PRICE_RE = re.compile(
        r'(\$|€|£|¥|₹|usd\s*|eur\s*|gbp\s*|jpy\s*|inr\s?)\s?(\d+(?:[.,]\d{1,2})?)',
        re.IGNORECASE
    )
    _CURRENCY_MAP = {"$": "usd", "€": "eur", "£": "gbp", "¥": "jpy", "₹": "inr"}
    _SECTION_HEADS = ["h2", "h3", "h4"]

    # Build a flat ordered list of (element, heading_text) tuples so each
    # price node can be associated with the closest preceding section heading.
    page_h1 = h1s[0].get_text(strip=True) if h1s else "Unknown"
    body = soup.find("body") or soup

    def _nearest_section_head(node) -> str:
        """Walk up then backwards to find closest preceding h2/h3/h4."""
        for parent in node.parents:
            # Try siblings before this node inside each ancestor
            for sib in parent.children:
                if sib == node or sib == parent:
                    break
                if hasattr(sib, 'name') and sib.name in _SECTION_HEADS:
                    text = sib.get_text(strip=True)
                    if text:
                        return text
            if hasattr(parent, 'name') and parent.name in _SECTION_HEADS:
                text = parent.get_text(strip=True)
                if text:
                    return text
        return page_h1

    def _billing_period(context_text: str) -> str:
        m = _PERIOD_RE.search(context_text)
        if not m:
            return "one-time"
        word = m.group(1).lower()
        return "monthly" if word == "month" else "yearly"

    def _is_strikethrough(node) -> bool:
        """Return True if node or any ancestor signals a struck-through price."""
        for parent in [node] + list(node.parents):
            if hasattr(parent, 'name'):
                if parent.name in _STRIKETHROUGH_TAGS:
                    return True
                classes = " ".join(parent.get("class", []))
                if re.search(r"(strike|line.?through|original.?price|was.?price)", classes, re.I):
                    return True
        return False

    seen_price_keys: set = set()
    for tag in body.find_all(string=_PRICE_RE):
        m = _PRICE_RE.search(str(tag))
        if not m:
            continue
        try:
            currency_raw = m.group(1).strip().lower().rstrip()
            val = str(float(m.group(2).replace(',', '.')))
        except ValueError:
            continue

        currency = _CURRENCY_MAP.get(currency_raw, currency_raw)
        parent_node = tag.parent if hasattr(tag, 'parent') else None
        if parent_node is None:
            continue

        # Determine qualifier: original/promotional or current
        qualifier = "current"
        if _is_strikethrough(parent_node):
            qualifier = "original"
        else:
            surrounding = (parent_node.get_text(" ", strip=True) if hasattr(parent_node, 'get_text') else "")
            if _PROMO_WORDS.search(surrounding):
                qualifier = "promotional"

        # Scope to nearest section heading to avoid lumping all products together
        entity_subject = _nearest_section_head(parent_node)
        # Context text around the price tag (up to 120 chars) for period detection
        ctx = (parent_node.get_text(" ", strip=True) if hasattr(parent_node, 'get_text') else "")[:120]
        period = _billing_period(ctx)

        key = (entity_subject, val, currency, period, qualifier)
        if key in seen_price_keys:
            continue
        seen_price_keys.add(key)

        facts.append(StructuredFact(
            fact_type="price",
            value=val,
            source=source,
            page_url=HttpUrl(url),
            currency=currency,
            billing_period=period,
            entity=page_h1,
            entity_subject=entity_subject,
            price_qualifier=qualifier,
        ))

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
    
    # Patterns that indicate decorative/non-informational images
    _decorative_patterns = re.compile(r'(logo|icon|placeholder|banner|hero|bg|background|sprite|spacer|pixel|tracking)', re.I)
    
    for img in soup.find_all('img'):
        parent = img.find_parent(['main', 'article', 'figure'])
        if not parent:
            continue
            
        alt = img.get('alt', '')
        src = img.get('src', '').lower()
        img_class = ' '.join(img.get('class', [])).lower()
        
        # Skip if has meaningful alt text
        if alt and alt.strip():
            continue
            
        # Skip if likely decorative based on src
        if _decorative_patterns.search(src) or _decorative_patterns.search(img_class):
            continue
            
        # Skip very small images (likely icons/spacers)
        width = img.get('width', '')
        height = img.get('height', '')
        if width and height:
            try:
                if int(width) < 50 or int(height) < 50:
                    continue
            except ValueError:
                pass
        
        # Check if the image looks like it contains primary factual content (charts, infographics, product stats)
        is_factual = any(kw in src or kw in img_class for kw in ['chart', 'graph', 'data', 'stat', 'infographic', 'price'])
        
        context_parent = img.find_parent(['figure', 'picture']) or img.find_parent(class_=re.compile(r'product|item|detail|gallery', re.I))
        
        if (context_parent or parent.name in ['main', 'article']) and is_factual:
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
