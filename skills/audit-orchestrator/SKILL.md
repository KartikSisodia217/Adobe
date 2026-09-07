---
name: audit-orchestrator
description: Safely coordinates a read-only public website audit for AI discoverability and on-site engagement, composes specialized evidence, and emits one Adobe Round 3 compliant report. Use when given a public website URL to audit.
license: MIT
compatibility: Requires HTTPS GET access, a sandboxed browser for rendered checks, and Python or JavaScript runtime support. Does not use authenticated access or modify sites.
---
# Brand AI-Readiness Audit (discoverability + engagement)

## When to use
Use this skill when you need to audit a brand's website for AI discoverability (e.g., crawler blocks, JS-rendering gaps, structured data integrity) and on-site engagement (e.g., unnamed controls, modal traps, blocked public routes). 

## Inputs
{"input_url": "https://example.com"}

## Procedure
1. Validate URL and perform security checks.
2. Initialize budget and `AuditContext`.
3. Discover/select pages (home, sitemap, links).
4. Run raw fetches and parse headers/metadata.
5. Invoke access-content-auditor for robots/content rules.
6. Start sandboxed browser and render selected pages.
7. Invoke engagement-auditor on browser adapter.
8. Invoke fact-integrity-auditor for entity consistency.
9. Fuse evidence, deduplicate, calculate confidence/severity, and cap findings.
10. Validate and emit Adobe-compliant JSON report.

## Output
A strictly typed JSON report conforming to the Adobe Round 3 schema containing site, audited_at, summary, coverage limitations, findings, and proactive_suggestions.
