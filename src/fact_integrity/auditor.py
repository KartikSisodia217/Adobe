"""Bounded, deterministic fact-integrity detectors for Member 3."""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from datetime import date
from typing import Awaitable, Callable, Iterable, Optional

import aiohttp

from src.schemas.v1 import AuditContext, CandidateFinding, StructuredFact

WikidataLookup = Callable[[str], Awaitable[list[dict]]]
_DATE = re.compile(r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b")
_EXPIRY_WORDS = re.compile(r"\b(expir(?:es|ed|y)|valid (?:until|through)|offer ends?)\b", re.I)
_PRICE = re.compile(r"(?:[\$\€\£\¥\₹]|usd\s?|eur\s?|gbp\s?|jpy\s?|inr\s?)(\d+(?:[.,]\d{1,2})?)", re.I)
_GENERIC_IDENTITIES = {"company", "official", "website", "brand", "our company", "business"}


def _normalise(value: str, fact_type: str) -> str:
    value = " ".join(value.casefold().split())
    if fact_type == "price":
        match = _PRICE.search(value)
        return match.group(1) if match else value
    return value


def _finding(detector_id: str, mechanism: str, entity: str, evidence: list[dict],
             page_urls: list, confidence: str = "high") -> CandidateFinding:
    return CandidateFinding(
        detector_id=detector_id,
        mechanism=mechanism,
        confidence=confidence,
        affected_entity=entity,
        evidence_items=evidence,
        category="discoverability",
        page_urls=page_urls,
    )


def _expired_claims(facts: Iterable[StructuredFact], today: date) -> list[CandidateFinding]:
    findings = []
    for fact in facts:
        if not _EXPIRY_WORDS.search(fact.value):
            continue
        match = _DATE.search(fact.value)
        if not match:
            continue
        claim_date = date(*map(int, match.groups()))
        if claim_date < today:
            findings.append(_finding(
                "F-01", "expired-claim", fact.value,
                [{"value": fact.value, "date": claim_date.isoformat(), "source": fact.source,
                  "page_url": str(fact.page_url)}], [fact.page_url],
            ))
    return findings


def build_fact_identity(fact: StructuredFact) -> tuple:
    """Builds a normalized identity to ensure we only compare related facts."""
    # Scope to entity name if known, otherwise scope to the specific page URL
    # to prevent falsely comparing different unknown products across the site.
    scope = fact.entity.casefold() if fact.entity and fact.entity != "Unknown" else str(fact.page_url)
    
    return (
        scope,
        fact.fact_type,
        fact.currency.casefold() if fact.currency else "unknown",
        fact.billing_period.casefold() if fact.billing_period else "unknown",
        fact.offer_type.casefold() if fact.offer_type else "unknown"
    )

def _contradictions(facts: Iterable[StructuredFact]) -> list[CandidateFinding]:
    groups: dict[tuple, list[StructuredFact]] = defaultdict(list)
    for fact in facts:
        identity = build_fact_identity(fact)
        groups[identity].append(fact)
        
    findings = []
    for identity, group in groups.items():
        fact_type = identity[1]
        if fact_type not in {"price", "availability", "organization_name", "contact"}:
            continue
            
        values = defaultdict(list)
        for fact in group:
            values[_normalise(fact.value, fact_type)].append(fact)
            
        if len(values) < 2:
            continue
            
        evidence = [
            {"fact_type": fact_type, "value": fact.value, "source": fact.source, "page_url": str(fact.page_url), "identity": identity}
            for members in values.values() for fact in members
        ]
        urls = list(dict.fromkeys(fact.page_url for members in values.values() for fact in members))
        findings.append(_finding("F-02", "first-party-contradiction", fact_type, evidence, urls))
    return findings


def _generic_identity(value: str) -> bool:
    normal = _normalise(value, "organization_name")
    return normal in _GENERIC_IDENTITIES or len(normal) < 4 or normal.startswith(("the company", "our "))


async def _wikidata_search(query: str) -> list[dict]:
    timeout = aiohttp.ClientTimeout(total=3)
    params = {"action": "wbsearchentities", "search": query, "language": "en", "format": "json", "limit": 5}
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get("https://www.wikidata.org/w/api.php", params=params) as response:
            response.raise_for_status()
            return (await response.json()).get("search", [])[:5]


async def _entity_ambiguity(context: AuditContext, facts: list[StructuredFact],
                            contradictions: list[CandidateFinding], lookup: Optional[WikidataLookup]) -> list[CandidateFinding]:
    identities = [fact for fact in facts if fact.fact_type == "organization_name"]
    if not identities:
        return []
    distinct = list(dict.fromkeys(_normalise(fact.value, fact.fact_type) for fact in identities))
    generic = all(_generic_identity(fact.value) for fact in identities)
    lacks_same_as = not any("sameas" in fact.value.casefold() for fact in identities)
    contradictory = any(f.affected_entity == "organization_name" for f in contradictions)
    if not generic and len(distinct) == 1:
        return []
    evidence = [{"value": fact.value, "source": fact.source, "page_url": str(fact.page_url)} for fact in identities]
    urls = list(dict.fromkeys(fact.page_url for fact in identities))
    findings = [_finding("F-03", "ambiguous-first-party-identity", "organization identity", evidence, urls, "medium")]

    # One lookup is permitted only for the narrow triage condition in the specification.
    if not (generic and lacks_same_as and contradictory):
        return findings
    try:
        results = await (lookup or _wikidata_search)(identities[0].value)
        context.budgets_consumed["wikidata_calls"] = context.budgets_consumed.get("wikidata_calls", 0) + 1
        if len(results[:5]) > 1:
            findings.append(_finding(
                "F-04", "bounded-wikidata-ambiguity-signal", "organization identity",
                evidence + [{"external_candidates": len(results[:5]), "source": "wikidata", "not_absolute_truth": True}],
                urls, "medium",
            ))
    except (asyncio.TimeoutError, aiohttp.ClientError, OSError, ValueError) as exc:
        context.record_limitation(f"Wikidata lookup unavailable: {type(exc).__name__}")
    return findings


async def run_fact_integrity(context: AuditContext, facts: Iterable[StructuredFact], *,
                             wikidata_lookup: Optional[WikidataLookup] = None,
                             today: Optional[date] = None) -> list[CandidateFinding]:
    """Run independent deterministic fact checks without allowing lookup failure to abort them."""
    materialised = list(facts)
    expired = _expired_claims(materialised, today or date.today())
    contradictions = _contradictions(materialised)
    identity = await _entity_ambiguity(context, materialised, contradictions, wikidata_lookup)
    return expired + contradictions + identity
