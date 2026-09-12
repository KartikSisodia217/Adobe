---
name: audit-orchestrator
description: Safely coordinates a read-only public website audit for AI discoverability and on-site engagement, composes specialized evidence, and emits one Adobe Round 3 compliant report. Use when given a public website URL to audit.
license: MIT
compatibility: Requires HTTPS GET access, a sandboxed browser for rendered checks, and Python or JavaScript runtime support. Does not use authenticated access or modify sites.
---
# Brand AI-Readiness Audit (discoverability + engagement)

## When to use
Use this skill when you need to audit a brand's website for AI discoverability (e.g., crawler blocks, JS-rendering gaps, structured data integrity) and on-site engagement (e.g., unnamed controls, modal traps, blocked public routes). 

## Orchestration Rules & Reasoning

### URL & Security Pinning
*   **Rule:** Resolve and pin the original input URL immediately to prevent DNS rebinding or SSRF attacks. Ensure this pinned destination is strictly adhered to for all downstream fetches.
*   **Reasoning:** Prevents the auditor from accidentally attacking internal resources.

### Semantic Candidate Selection
*   **Rule:** The crawler must perform true semantic page-role selection. It should infer the page role based on the title, H1, JSON-LD schema, breadcrumbs, and anchor text context rather than just URL pattern heuristics.
*   **Reasoning:** Ensures generalization to unseen websites (e.g., distinguishing a Next.js dynamic route `/p/abc` as a product page based on semantic content).

### Evidence Fusion & Capping
*   **Rule:** Deduplicate findings from multiple sub-auditors if they refer to the same mechanism and entity.
*   **Severity Criteria:** Severity is based on Impact × Scope × Mechanism (independent of confidence). For example, a missing Product schema on one blog page has lower severity than every product page being invisible.
*   **Capping Output:** Always report the total number of detected findings vs the number of suppressed (capped) findings in the final JSON summary to preserve transparency regarding the audit's true coverage.

### Output
A strictly typed JSON report conforming to the Adobe Round 3 schema containing site, audited_at, summary (with detection/suppression stats), coverage limitations, findings, and proactive_suggestions.
