"""Bounded, read-only checks for authoritative-source clarity.

External observations are supplied by a caller or collected as outbound references on
the audited site.  This module deliberately does not treat search rank or mention
count as truth, and it never labels a source malicious without direct evidence.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from src.schemas.v1 import AuditContext, CandidateFinding

_ACTION = re.compile(r"buy|purchase|order|book|sign.?up|register|contact|apply|enroll|subscribe", re.I)
_OFFICIAL = re.compile(r"official (site|website|domain|source)|all (purchases|orders|bookings|signups).{0,40}(through|at)|no longer.{0,40}(sell|available|use)", re.I)
_SOCIAL = {"linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com", "tiktok.com"}


@dataclass(frozen=True)
class Claim:
    fact: str
    value: str
    source_url: str
    source_kind: str
    confidence: str = "high"
    entity: str = "brand"
    timestamp: str | None = None
    context: str = ""


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _nodes(value: Any) -> Iterable[dict]:
    if isinstance(value, list):
        for entry in value:
            yield from _nodes(entry)
    elif isinstance(value, dict):
        if "@graph" in value:
            yield from _nodes(value["@graph"])
        yield value


def _claims_from_html(html: str, source_url: str, kind: str) -> list[Claim]:
    soup = BeautifulSoup(html, "lxml")
    claims: list[Claim] = []
    canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
    if canonical and canonical.get("href"):
        claims.append(Claim("official_domain", _host(urljoin(source_url, canonical["href"])), source_url, kind, context="canonical URL"))
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(script.get_text(strip=True))
        except (ValueError, TypeError):
            continue
        for node in _nodes(payload):
            types = node.get("@type", [])
            types = [types] if isinstance(types, str) else types
            if any(t in {"Organization", "Corporation", "LocalBusiness", "Person"} for t in types):
                if node.get("name"):
                    claims.append(Claim("organization_name", str(node["name"]), source_url, kind, context="Organization JSON-LD"))
                if node.get("url"):
                    claims.append(Claim("official_domain", _host(str(node["url"])), source_url, kind, context="Organization JSON-LD URL"))
                for same_as in node.get("sameAs", []) if isinstance(node.get("sameAs"), list) else []:
                    claims.append(Claim("same_as", str(same_as), source_url, kind, context="Organization sameAs"))
    page_text = soup.get_text(" ", strip=True)
    if _OFFICIAL.search(page_text):
        claims.append(Claim("official_clarity", "declared", source_url, kind, context=_OFFICIAL.search(page_text).group(0)))
    for price in re.findall(r"(?:[$€£¥₹]|USD\s?|EUR\s?|INR\s?)\s?\d+(?:[.,]\d{1,2})?", page_text, re.I):
        claims.append(Claim("price", price, source_url, kind, context="visible page text"))
    for email in re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", page_text, re.I):
        claims.append(Claim("contact", email, source_url, kind, context="visible page text"))
    for anchor in soup.find_all("a", href=True):
        destination = urljoin(source_url, anchor["href"])
        if not destination.startswith(("http://", "https://")):
            continue
        label = anchor.get_text(" ", strip=True)
        nearby = " ".join(anchor.parent.stripped_strings) if anchor.parent else label
        if _ACTION.search(label + " " + nearby):
            claims.append(Claim("destination", destination, source_url, kind, context=(label or nearby)[:180]))
    return claims


def _external_claims(external_sources: list[dict]) -> list[Claim]:
    claims: list[Claim] = []
    for source in external_sources:
        url = str(source.get("url", ""))
        if not url.startswith(("http://", "https://")):
            continue
        if isinstance(source.get("html"), str):
            claims.extend(_claims_from_html(source["html"], url, "external"))
        for fact, value in (source.get("claims") or {}).items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                claims.append(Claim(str(fact), str(item), url, "external", str(source.get("confidence", "medium")), timestamp=source.get("timestamp"), context=str(source.get("label", "external observation"))))
    return claims


def _candidate(detector_id: str, mechanism: str, entity: str, evidence: list[dict], urls: list[str], confidence: str = "high") -> CandidateFinding:
    return CandidateFinding(detector_id=detector_id, mechanism=mechanism, confidence=confidence,
        affected_entity=entity, evidence_items=evidence, category="brand-identity", page_urls=[HttpUrl(u) for u in urls])


def _queries(name: str, domain: str, destinations: list[Claim]) -> list[dict]:
    subject = name or domain
    questions = [
        (f"What is the official website of {subject}?", "official domain"),
        (f"Who provides {subject}?", "organization identity"),
        (f"What is the current contact destination for {subject}?", "contact or official destination"),
    ]
    if destinations:
        questions.append((f"Where can I buy, book, or sign up with {subject}?", "current authoritative destination"))
    return [{"question": q, "required_fact": fact, "method": "Check first-party clarity and observed public-source agreement; this does not simulate an AI answer."} for q, fact in questions]


def run_brand_identity_audit(context: AuditContext) -> list[CandidateFinding]:
    """Compare current first-party authority claims with bounded observed sources."""
    first_party = [claim for page in context.raw_pages for claim in _claims_from_html(page.html_content, str(page.url), "first_party")]
    external = _external_claims(context.external_sources)
    site_domain = _host(str(context.target_url))
    official_domains = {site_domain}
    official_domains.update(c.value for c in first_party if c.fact == "official_domain" and c.value)
    names = [c.value for c in first_party if c.fact == "organization_name"]
    destinations = [c for c in first_party if c.fact == "destination"]
    context.query_simulation = _queries(names[0] if names else "", site_domain, destinations)
    findings: list[CandidateFinding] = []

    # An action destination is only concerning when an independently observed source
    # associates the same brand/action with a different host. Social/sameAs links are excluded.
    external_destinations = [c for c in external if c.fact in {"destination", "purchase_destination", "contact_destination", "signup_destination"}]
    first_hosts = {_host(c.value) for c in destinations}
    for claim in external_destinations:
        observed_host = _host(claim.value)
        if not observed_host or observed_host in official_domains or observed_host in _SOCIAL:
            continue
        if first_hosts and observed_host not in first_hosts:
            evidence = [
                {"source": str(context.target_url), "fact": "official_domain", "value": site_domain, "confidence": "high"},
                {"source": claim.source_url, "fact": claim.fact, "value": claim.value, "confidence": claim.confidence, "timestamp": claim.timestamp, "context": claim.context},
            ]
            findings.append(_candidate("B-01", "conflicting authoritative destination", "purchase/contact/signup destination", evidence, [str(context.target_url), claim.source_url]))

    # Same entity/name attached to materially different domains is ambiguity, not proof of impersonation.
    external_names = [c for c in external if c.fact == "organization_name"]
    for ext_name in external_names:
        if names and ext_name.value.casefold() == names[0].casefold() and _host(ext_name.source_url) not in official_domains:
            findings.append(_candidate("B-03", "same-name entity ambiguity", ext_name.value, [
                {"source": str(context.target_url), "fact": "organization_name", "value": names[0], "confidence": "high"},
                {"source": ext_name.source_url, "fact": "organization_name", "value": ext_name.value, "confidence": ext_name.confidence},
            ], [str(context.target_url), ext_name.source_url], "medium"))
            break

    # Compare supplied source facts rather than guessing which age/value is correct.
    for claim in external:
        if claim.fact not in {"price", "availability", "contact", "official_domain"}:
            continue
        matches = [c for c in first_party if c.fact == claim.fact and c.value.casefold() != claim.value.casefold()]
        if matches:
            first = matches[0]
            findings.append(_candidate("B-02", "potentially stale or conflicting fact", claim.fact, [
                {"source": first.source_url, "fact": first.fact, "value": first.value, "confidence": first.confidence},
                {"source": claim.source_url, "fact": claim.fact, "value": claim.value, "confidence": claim.confidence, "timestamp": claim.timestamp},
            ], [first.source_url, claim.source_url], "high"))

    if findings and not any(c.fact == "official_clarity" for c in first_party):
        findings.append(_candidate("B-04", "official-source clarity gap", "authoritative brand destination", [
            {"source": str(context.target_url), "observed": "No explicit official-site or current-destination statement found"},
            {"conflicts_observed": len(findings)},
        ], [str(context.target_url)], "medium"))
    return findings
