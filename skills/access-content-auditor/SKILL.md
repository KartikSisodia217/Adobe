---
name: access-content-auditor
description: Audits declared crawler access, raw public content, canonical URLs, structured facts, and important render-only content without altering a website. Use during a public AI-discoverability audit.
license: MIT
compatibility: Requires safe HTTP GET access and optional sandboxed browser snapshots supplied by the orchestrator.
---
# Access and Content Auditor

## When to use
Use during a public AI-discoverability audit to check if pages can be crawled and if important content is trapped in JavaScript or missing structured data.

## Detection Rules & Reasoning

### D-01: Retrieval Access Restriction
*   **Detection Conditions:** Check if `robots.txt` explicitly disallows AI agents (e.g. `OAI-SearchBot`, `GPTBot`, `ClaudeBot`).
*   **Evidence Requirements:** Must record the exact bot name and the blocked path.
*   **False-Positive Exclusions:** Do not flag generic `User-Agent: *` blocks as AI-specific unless accompanied by AI bot names.
*   **Severity Criteria:** Critical if blocking entire site (`/`); Medium if blocking specific subdirectories.

### D-02: Entity-Aware Schema Contradiction
*   **Detection Conditions:** Check if JSON-LD declares prices/facts that don't exist visibly under the same context.
*   **Evidence Requirements:** Must extract currency, billing period, and offer type before declaring a contradiction.
*   **False-Positive Exclusions:** `$49/month` visible and `$499/year` visible vs `499` in JSON-LD is NOT a contradiction if the billing periods differ. Match on entity properties.
*   **Severity Criteria:** Medium (impacts disambiguation but site remains crawlable).

### E-01: JS Rendering Gap
*   **Detection Conditions:** Core facts (pricing, titles, availability) appear in hydration but are missing in raw HTML.
*   **Evidence Requirements:** Must prove fact is material to the inferred page role (e.g. price on a product detail page).
*   **False-Positive Exclusions:** Do NOT report a gap merely because a fact appears after hydration. Report only if no equivalent exists in raw HTML/JSON-LD and the rendered fact is extractable with high confidence using semantic/fuzzy matching (85%+ similarity threshold).
*   **Severity Criteria:** High (prevents static AI indexers from extracting essential data).

### Action Selection & Remediation
*   For D-01: Suggest `Allow: /` in `robots.txt`.
*   For E-01: Recommend Server-Side Rendering (SSR) or Static Site Generation (SSG) for core data.
*   For D-02: Recommend JSON-LD synchronization with visual data.
