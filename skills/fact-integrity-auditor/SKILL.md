---
name: fact-integrity-auditor
description: Checks sampled first-party website facts for material contradictions and evaluates whether public organization identity is sufficiently anchored, using one bounded knowledge-graph lookup only when needed. Use during a public AI-discoverability audit.
license: MIT
compatibility: Requires normalized page facts and optional HTTPS access to Wikidata. Does not use general web search.
---
# Fact Integrity Auditor

## When to use
Use during a public AI-discoverability audit to detect conflicting facts (prices, dates) or ambiguous brand identities.

## Inputs
`StructuredFact`s collected from the audit context.

## Procedure
1. Construct provenance graph of facts.
2. Normalize comparable facts (dates, prices).
3. Find material first-party contradictions.
4. Apply qualified entity decision tree (optional bounded Wikidata corroboration).
5. Return candidate findings.

## Output
Candidate findings for first-party contradictions and entity ambiguity.
