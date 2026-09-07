---
name: access-content-auditor
description: Audits declared crawler access, raw public content, canonical URLs, structured facts, and important render-only content without altering a website. Use during a public AI-discoverability audit.
license: MIT
compatibility: Requires safe HTTP GET access and optional sandboxed browser snapshots supplied by the orchestrator.
---
# Access and Content Auditor

## When to use
Use during a public AI-discoverability audit to check if pages can be crawled and if important content is trapped in JavaScript or missing structured data.

## Inputs
`AuditContext` containing `RawPage` and `RenderedPage` snapshots.

## Procedure
1. Parse robots policy.
2. Parse raw HTTP responses for facts and canonicals.
3. Extract JSON-LD and meta tags.
4. Compare raw text equivalents against rendered important facts.
5. Return candidate findings and structured facts to the orchestrator.

## Output
Candidate findings for D-01, D-02, E-01, E-02.
