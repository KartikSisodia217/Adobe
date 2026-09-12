---
name: fact-integrity-auditor
description: Checks sampled first-party website facts for material contradictions and evaluates whether public organization identity is sufficiently anchored, using one bounded knowledge-graph lookup only when needed. Use during a public AI-discoverability audit.
license: MIT
compatibility: Requires normalized page facts and optional HTTPS access to Wikidata. Does not use general web search.
---
# Fact Integrity Auditor

## When to use
Use during a public AI-discoverability audit to detect conflicting facts (prices, dates) or ambiguous brand identities.

## Detection Rules & Reasoning

### First-Party Contradiction (F-01, F-02)
*   **Detection Conditions:** Check if the exact same entity fact (e.g., price, offer expiration) contradicts itself across different pages on the same site.
*   **Evidence Requirements:** Must extract fact source (URL/Context) and the normalized contrasting values.
*   **False-Positive Exclusions:** Ensure values are normalized before comparing (e.g., £49.00 vs £49). Do not flag differing prices if they refer to different products or billing periods.
*   **Severity Criteria:** High (hallucination risk if an LLM is asked for the price).

### F-03: Identity Ambiguity Signal
*   **Detection Conditions:** Check if the organization's public identity is sufficiently anchored on its homepage.
*   **Evidence Requirements:** Analyze homepage title, H1, meta description, and JSON-LD Organization schema for strong, unique branding.
*   **False-Positive Exclusions:** A lack of external Wikidata presence does NOT automatically mean the entity is incorrect. The Wikidata lookup is purely an evidentiary corroboration check, not a ground-truth gate. The primary signal is whether the first-party identity looks weak (e.g., generic names like "Company", "Official Website").
*   **Severity Criteria:** Medium (affects citation resilience and canonical entity linking).

### Action Selection & Remediation
*   For Contradictions: Consolidate conflicting facts into a single authoritative truth source.
*   For F-03: Inject `sameAs` canonical identity references and authoritative external corroboration links into the JSON-LD Organization schema.
