"""Bounded, read-only checks for authoritative-source clarity and cross-web presence.

Compares official identity and action destinations with bounded observed public sources
to surface conflicting destinations, stale prices, entity ambiguity, and outdated representations.
Does NOT call sources malicious without direct evidence; uses evidence-backed neutral classifications.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from src.schemas.v1 import AuditContext, CandidateFinding

_ACTION = re.compile(
    r"buy|purchase|order|book|sign.?up|register|contact|apply|enroll|subscribe|login|checkout|pricing|get\s+started|join",
    re.I
)
_OFFICIAL = re.compile(
    r"official (site|website|domain|source)|all (purchases|orders|bookings|signups|enrollments).{0,50}(through|at)|"
    r"only official|no longer.{0,50}(sell|available|use|support)|previously (hosted|known)|migrated to",
    re.I
)
_HISTORICAL_KEYWORDS = re.compile(
    r"previously|former|legacy|old platform|archived|no longer active|migrated|we have moved|deprecated",
    re.I
)
_RESELLER_KEYWORDS = re.compile(
    r"authorized reseller|official reseller|reseller partner|distributor partner|affiliate program|authorized distributor|\breseller\b",
    re.I
)

_SOCIAL_HOSTS = {
    "linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com",
    "youtube.com", "tiktok.com", "github.com", "pinterest.com"
}


@dataclass(frozen=True)
class Claim:
    fact: str
    value: str
    source_url: str
    source_kind: str  # "first_party" or "external"
    confidence: str = "high"
    entity: str = "brand"
    timestamp: str | None = None
    context: str = ""


@dataclass
class SourceProfile:
    url: str
    domain: str
    classification: str  # "first-party", "historical first-party", "third-party", "reseller", "marketplace", "unknown"
    connecting_evidence: List[Dict[str, str]] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    confidence: str = "medium"


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _clean_handle(url_or_handle: str) -> str:
    """Normalize social profile URLs to clean handles for cross-source matching."""
    parsed = urlparse(url_or_handle)
    path = parsed.path.strip("/")
    # Handle /@user or /in/user or /company/user
    parts = path.split("/")
    if parts:
        last = parts[-1].lstrip("@").lower()
        if last in {"", "login", "signup"}:
            return path.lower()
        return last
    return url_or_handle.lower()


def _nodes(value: Any) -> Iterable[dict]:
    if isinstance(value, list):
        for entry in value:
            yield from _nodes(entry)
    elif isinstance(value, dict):
        if "@graph" in value:
            yield from _nodes(value["@graph"])
        yield value


def _normalize_price(raw: str) -> str:
    """Extract numeric value and currency symbol cleanly."""
    return " ".join(raw.strip().split())


def _claims_from_html(html: str, source_url: str, kind: str) -> list[Claim]:
    soup = BeautifulSoup(html, "lxml")
    claims: list[Claim] = []
    host = _host(source_url)

    # 1. Canonical URL
    canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
    if canonical and canonical.get("href"):
        canon_host = _host(urljoin(source_url, canonical["href"]))
        if canon_host:
            claims.append(Claim("canonical_domain", canon_host, source_url, kind, context="canonical URL tag"))

    # 2. JSON-LD structured data
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(script.get_text(strip=True))
        except Exception:
            continue
        for node in _nodes(payload):
            types = node.get("@type", [])
            types = [types] if isinstance(types, str) else types

            # Organization / Person
            if any(t in {"Organization", "Corporation", "LocalBusiness", "Person", "EducationalOrganization"} for t in types):
                if node.get("name"):
                    claims.append(Claim("organization_name", str(node["name"]).strip(), source_url, kind, context=f"{types[0]} JSON-LD"))
                if node.get("url"):
                    claims.append(Claim("official_domain", _host(str(node["url"])), source_url, kind, context="Organization URL"))
                for same_as in node.get("sameAs", []) if isinstance(node.get("sameAs"), list) else ([node.get("sameAs")] if node.get("sameAs") else []):
                    if isinstance(same_as, str) and same_as.startswith("http"):
                        claims.append(Claim("same_as", same_as.strip(), source_url, kind, context="Organization sameAs"))

            # Product / Course
            if any(t in {"Product", "Course", "SoftwareApplication"} for t in types):
                p_name = node.get("name")
                if p_name:
                    claims.append(Claim("product_name", str(p_name).strip(), source_url, kind, context=f"{types[0]} Schema"))
                offers = node.get("offers")
                offer_list = offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []
                for off in offer_list:
                    price = off.get("price")
                    curr = off.get("priceCurrency", "")
                    if price is not None:
                        claims.append(Claim("price", f"{curr} {price}".strip(), source_url, kind, context=f"{types[0]} offer price"))
                    avail = off.get("availability")
                    if avail:
                        claims.append(Claim("availability", str(avail).split("/")[-1], source_url, kind, context=f"{types[0]} availability"))
                    off_url = off.get("url")
                    if off_url and isinstance(off_url, str):
                        claims.append(Claim("destination", urljoin(source_url, off_url), source_url, kind, context=f"{types[0]} offer checkout"))

    # 3. Visible page text: official statements, prices, contacts
    page_text = soup.get_text(" ", strip=True)

    official_match = _OFFICIAL.search(page_text)
    if official_match:
        claims.append(Claim("official_clarity", "declared", source_url, kind, context=official_match.group(0)))

    if _HISTORICAL_KEYWORDS.search(page_text):
        claims.append(Claim("historical_notice", "present", source_url, kind, context="Explicit historical/legacy notice in page text"))

    if _RESELLER_KEYWORDS.search(page_text):
        claims.append(Claim("reseller_notice", "present", source_url, kind, context="Partner or reseller notice in page text"))

    # Extracted prices from page text
    price_regex = re.findall(r"(?:[$€£¥₹]|USD\s?|EUR\s?|INR\s?|Rs\.?\s?)\s?[\d,]+(?:\.\d{1,2})?", page_text, re.I)
    for price in list(dict.fromkeys(price_regex))[:10]:
        claims.append(Claim("price", _normalize_price(price), source_url, kind, context="visible page text"))

    # Contact emails
    for email in list(dict.fromkeys(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", page_text, re.I)))[:3]:
        claims.append(Claim("contact", email.lower(), source_url, kind, context="visible contact email"))

    # 4. Links and Anchors: Action URLs and Social Profiles
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        destination = urljoin(source_url, href)
        if not destination.startswith(("http://", "https://")):
            continue

        dest_host = _host(destination)
        label = anchor.get_text(" ", strip=True)
        nearby = " ".join(anchor.parent.stripped_strings) if anchor.parent else label
        combined_text = (label + " " + nearby)[:180].strip()

        # Social links
        if dest_host in _SOCIAL_HOSTS:
            handle = _clean_handle(destination)
            claims.append(Claim("social_link", destination, source_url, kind, context=f"{dest_host} profile ({handle})"))

        # Action / Purchase / Registration destinations
        if _ACTION.search(label) or _ACTION.search(href) or _ACTION.search(nearby):
            claims.append(Claim("destination", destination, source_url, kind, context=combined_text or label or "Action link"))

    # 5. OpenGraph, Title, and concise H1
    og_name = soup.find("meta", attrs={"property": "og:site_name"})
    if og_name and og_name.get("content"):
        claims.append(Claim("organization_name", og_name["content"].strip(), source_url, kind, context="og:site_name"))

    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text(" ", strip=True)
        if h1_text and len(h1_text) <= 50:
            claims.append(Claim("organization_name", h1_text, source_url, kind, context="Primary <h1> heading"))

    title = soup.find("title")
    if title and title.string:
        t_str = title.string.strip()
        claims.append(Claim("title", t_str, source_url, kind, context="Page <title>"))
        # Check for instructor or creator: e.g. "Brand by Person"
        by_match = re.search(r"by\s+([A-Za-z\s]+)", t_str, re.I)
        if by_match:
            claims.append(Claim("person_name", by_match.group(1).strip(), source_url, kind, context="Creator name in title"))

    return claims


def _external_claims(external_sources: list[dict]) -> tuple[list[Claim], list[SourceProfile]]:
    """Parse claims and profile each external source."""
    all_claims: list[Claim] = []
    profiles: list[SourceProfile] = []

    for source in external_sources:
        url = str(source.get("url", source.get("original_url", "")))
        if not url.startswith(("http://", "https://")):
            continue

        domain = _host(url)
        profile = SourceProfile(url=url, domain=domain, classification="unknown", confidence=str(source.get("confidence", "medium")))

        # From HTML if provided
        if isinstance(source.get("html"), str) and source["html"]:
            extracted = _claims_from_html(source["html"], url, "external")
            profile.claims.extend(extracted)
            all_claims.extend(extracted)

        # From explicit caller claims if provided
        for fact, value in (source.get("claims") or {}).items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                c = Claim(str(fact), str(item), url, "external", str(source.get("confidence", "medium")),
                          timestamp=source.get("timestamp"), context=str(source.get("label", "caller-provided claim")))
                profile.claims.append(c)
                all_claims.append(c)

        profiles.append(profile)

    return all_claims, profiles


def _classify_sources(
    profiles: list[SourceProfile],
    first_party_claims: list[Claim],
    site_domain: str,
    target_url: str
) -> None:
    """Evidence-backed classification of each external source."""
    official_domains = {site_domain}
    official_domains.update(c.value for c in first_party_claims if c.fact in {"official_domain", "canonical_domain"} and c.value)

    first_org_names = {c.value.casefold() for c in first_party_claims if c.fact == "organization_name"}
    first_person_names = {c.value.casefold() for c in first_party_claims if c.fact == "person_name"}
    first_social_handles = {_clean_handle(c.value) for c in first_party_claims if c.fact in {"social_link", "same_as"}}
    first_products = {c.value.casefold() for c in first_party_claims if c.fact == "product_name"}

    for p in profiles:
        ext_domain = p.domain
        ext_org_names = {c.value.casefold() for c in p.claims if c.fact == "organization_name"}
        ext_person_names = {c.value.casefold() for c in p.claims if c.fact == "person_name"}
        ext_social_handles = {_clean_handle(c.value) for c in p.claims if c.fact in {"social_link", "same_as"}}
        has_historical_notice = any(c.fact == "historical_notice" for c in p.claims)
        has_reseller_notice = any(c.fact == "reseller_notice" for c in p.claims)

        # Record connecting evidence anchors
        connecting: list[dict] = []
        shared_social = first_social_handles.intersection(ext_social_handles)
        for handle in shared_social:
            connecting.append({"anchor": "shared_social_channel", "value": handle})

        shared_org = first_org_names.intersection(ext_org_names)
        for org in shared_org:
            connecting.append({"anchor": "shared_brand_name", "value": org})

        shared_person = first_person_names.intersection(ext_person_names)
        for person in shared_person:
            connecting.append({"anchor": "shared_creator_or_founder", "value": person})

        p.connecting_evidence = connecting

        # 1. First-Party: Same primary domain, canonical, or verified official social channel
        is_official_social = (
            ext_domain in _SOCIAL_HOSTS and
            (_clean_handle(p.url) in first_social_handles or p.url in {c.value for c in first_party_claims if c.fact == "same_as"} or bool(shared_social))
        )
        if ext_domain in official_domains or ext_domain.endswith("." + site_domain) or is_official_social:
            p.classification = "first-party"
            p.confidence = "high"
            continue

        # 2. Reseller: Explicit reseller/partner notice
        if has_reseller_notice:
            p.classification = "reseller"
            p.confidence = "high"
            continue

        # 3. Known marketplace
        if any(market in ext_domain for market in ["amazon.", "ebay.", "udemy.com", "coursera.org", "walmart."]):
            p.classification = "marketplace"
            p.confidence = "high"
            continue

        # 4. Historical First-Party:
        # Shares identity anchors (social accounts, founder name, or brand name on platform)
        # or has explicit historical notice
        is_platform_host = any(p_host in ext_domain for p_host in [
            "classx.co.in", "teachable.com", "thinkific.com", "gumroad.com", "podia.com", "kajabi.com"
        ])

        if (shared_social or (shared_org and is_platform_host) or (shared_person and shared_org) or has_historical_notice):
            p.classification = "historical first-party"
            p.confidence = "high"
            continue

        # 5. Third-party platform or unrelated
        if shared_org:
            p.classification = "third-party"
            p.confidence = "medium"
        else:
            p.classification = "unknown"
            p.confidence = "low"


def _candidate(
    detector_id: str,
    mechanism: str,
    entity: str,
    evidence: list[dict],
    urls: list[str],
    confidence: str = "high"
) -> CandidateFinding:
    return CandidateFinding(
        detector_id=detector_id,
        mechanism=mechanism,
        confidence=confidence,
        affected_entity=entity,
        evidence_items=evidence,
        category="brand-identity",
        page_urls=[HttpUrl(u) for u in urls]
    )


def _queries(name: str, domain: str, destinations: list[Claim], profiles: list[SourceProfile]) -> list[dict]:
    subject = name or domain
    questions = [
        (f"What is the official website of {subject}?", "official domain"),
        (f"Who provides {subject}?", "organization identity"),
        (f"What is the current contact destination for {subject}?", "contact or official destination"),
    ]
    if destinations:
        questions.append((f"Where can I buy, book, or sign up with {subject}?", "current authoritative destination"))

    for p in profiles:
        if p.classification in {"historical first-party", "third-party", "reseller"}:
            questions.append((
                f"Is {p.domain} an official or current source for {subject}?",
                f"source classification: {p.classification}"
            ))

    return [
        {
            "question": q,
            "required_fact": fact,
            "method": "Check first-party clarity and observed public-source agreement; this does not simulate an AI answer."
        }
        for q, fact in questions
    ]


def run_brand_identity_audit(context: AuditContext) -> list[CandidateFinding]:
    """Compare current first-party authority claims with bounded observed sources."""
    first_party = [
        claim
        for page in context.raw_pages
        for claim in _claims_from_html(page.html_content, str(page.url), "first_party")
    ]
    external, profiles = _external_claims(context.external_sources)

    site_domain = _host(str(context.target_url))
    official_domains = {site_domain}
    official_domains.update(c.value for c in first_party if c.fact in {"official_domain", "canonical_domain"} and c.value)

    # Classify all discovered external sources
    _classify_sources(profiles, first_party, site_domain, str(context.target_url))

    # Update context with source profiles for downstream reporting
    for p in profiles:
        matching_ext = next((s for s in context.external_sources if _host(s.get("url", "")) == p.domain), None)
        if matching_ext:
            matching_ext["classification"] = p.classification
            matching_ext["connecting_evidence"] = p.connecting_evidence
            matching_ext["confidence"] = p.confidence

    names = [c.value for c in first_party if c.fact == "organization_name"]
    brand_name = names[0] if names else site_domain
    destinations = [c for c in first_party if c.fact == "destination"]

    context.query_simulation = _queries(brand_name, site_domain, destinations, profiles)
    findings: list[CandidateFinding] = []

    # Map first-party action destination hosts
    first_hosts = {_host(c.value) for c in destinations if _host(c.value)}
    if not first_hosts:
        first_hosts = {site_domain}

    # -------------------------------------------------------------
    # DETECTOR B-01: Conflicting Authoritative Destination (Critical)
    # -------------------------------------------------------------
    # An action destination (purchase, signup, login, checkout) conflicts when
    # an external representation (especially historical first-party or third-party)
    # points to a different non-official host.
    for profile in profiles:
        if profile.classification in {"first-party"}:
            continue

        ext_destinations = [c for c in profile.claims if c.fact in {"destination", "purchase_destination", "signup_destination"}]
        for claim in ext_destinations:
            dest_host = _host(claim.value)
            if not dest_host or dest_host in official_domains or dest_host in _SOCIAL_HOSTS:
                continue

            # If external destination is on an old host or third-party host not in official hosts
            if dest_host not in first_hosts:
                evidence = [
                    {
                        "source": str(context.target_url),
                        "fact": "official_destination",
                        "value": destinations[0].value if destinations else str(context.target_url),
                        "confidence": "high"
                    },
                    {
                        "source": claim.source_url,
                        "fact": claim.fact,
                        "value": claim.value,
                        "source_classification": profile.classification,
                        "connecting_evidence": profile.connecting_evidence,
                        "confidence": claim.confidence,
                        "context": claim.context
                    }
                ]
                findings.append(_candidate(
                    "B-01",
                    "conflicting authoritative destination",
                    "purchase/enrollment destination",
                    evidence,
                    [str(context.target_url), claim.source_url],
                    confidence="high"
                ))
                break  # Cap 1 B-01 per profile

    # -------------------------------------------------------------
    # DETECTOR B-02: Potentially Stale or Conflicting Fact (High)
    # -------------------------------------------------------------
    # Compare prices and availability across official and external representations.
    first_prices = [c for c in first_party if c.fact == "price"]
    first_price_values = {c.value.casefold() for c in first_prices}

    for profile in profiles:
        if profile.classification == "first-party":
            continue

        ext_prices = [c for c in profile.claims if c.fact == "price"]
        for ext_p in ext_prices:
            # Check if external price differs from first-party prices
            if first_prices and ext_p.value.casefold() not in first_price_values:
                first_match = first_prices[0]
                evidence = [
                    {
                        "source": first_match.source_url,
                        "fact": "official_price",
                        "value": first_match.value,
                        "confidence": "high"
                    },
                    {
                        "source": ext_p.source_url,
                        "fact": "external_price",
                        "value": ext_p.value,
                        "source_classification": profile.classification,
                        "connecting_evidence": profile.connecting_evidence,
                        "timestamp": ext_p.timestamp,
                        "confidence": ext_p.confidence
                    }
                ]
                findings.append(_candidate(
                    "B-02",
                    "potentially stale or conflicting fact",
                    f"pricing ({first_match.value} vs {ext_p.value})",
                    evidence,
                    [first_match.source_url, ext_p.source_url],
                    confidence="high"
                ))
                break  # Cap 1 price mismatch per external profile

    # -------------------------------------------------------------
    # DETECTOR B-05: Outdated Domain / Historical Platform Representation (High)
    # -------------------------------------------------------------
    # Active external presence identified as historical first-party that lacks
    # official delegation or redirection to the current official site.
    for profile in profiles:
        if profile.classification == "historical first-party":
            has_redirection = any(
                c.fact == "destination" and _host(c.value) in official_domains
                for c in profile.claims
            )
            has_official_notice = any(
                c.fact == "official_clarity"
                for c in profile.claims
            )
            # If historical platform does not point users to official site
            if not has_redirection and not has_official_notice:
                evidence = [
                    {
                        "source": str(context.target_url),
                        "fact": "official_domain",
                        "value": site_domain,
                        "confidence": "high"
                    },
                    {
                        "source": profile.url,
                        "fact": "historical_representation",
                        "value": profile.domain,
                        "classification": profile.classification,
                        "connecting_evidence": profile.connecting_evidence,
                        "issue": "Historical platform remains discoverable but lacks current official domain link or redirect."
                    }
                ]
                findings.append(_candidate(
                    "B-05",
                    "outdated platform representation",
                    "historical brand presence",
                    evidence,
                    [str(context.target_url), profile.url],
                    confidence="high"
                ))

    # -------------------------------------------------------------
    # DETECTOR B-03: Entity / Official-Source Ambiguity (Medium)
    # -------------------------------------------------------------
    # Same brand name presented on another domain without clear identity anchors
    for profile in profiles:
        if profile.classification in {"first-party", "reseller", "historical first-party"} or profile.domain in _SOCIAL_HOSTS:
            continue
        ext_orgs = [c.value for c in profile.claims if c.fact == "organization_name"]
        for ext_name in ext_orgs:
            if names and ext_name.casefold() == names[0].casefold() and profile.domain not in official_domains:
                findings.append(_candidate(
                    "B-03",
                    "same-name entity ambiguity",
                    ext_name,
                    [
                        {"source": str(context.target_url), "fact": "organization_name", "value": names[0], "confidence": "high"},
                        {"source": profile.url, "fact": "organization_name", "value": ext_name, "classification": profile.classification, "confidence": profile.confidence},
                    ],
                    [str(context.target_url), profile.url],
                    confidence="medium"
                ))
                break

    # -------------------------------------------------------------
    # DETECTOR B-04: Official-Source Clarity Gap (Medium)
    # -------------------------------------------------------------
    # If external conflicts or multiple representations exist, check if official site declares official authority
    if findings and not any(c.fact == "official_clarity" for c in first_party):
        findings.append(_candidate(
            "B-04",
            "official-source clarity gap",
            "authoritative brand destination",
            [
                {"source": str(context.target_url), "observed": "No explicit official-site or authoritative-destination statement found on primary pages."},
                {"conflicts_observed": len(findings)},
            ],
            [str(context.target_url)],
            confidence="medium"
        ))

    return findings
