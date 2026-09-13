# Detection Checklist & Evidence Guidelines

## Evidence and Exclusions

- **Establish First-Party Authority:** Derive official authority from the audited hostname, canonical URL tag, Organization / Person JSON-LD, visible official-source statements, verified social links (`sameAs`), and primary action destinations.
- **Bounded External Discovery:** Discover candidate representations via outbound platform links from first-party pages and bounded public search queries (with strict rate bounds, robots.txt checks, and SSRF guards).
- **Evidence-Backed Classification:** Never accuse an external site of being malicious, fraudulent, or a scam without direct proof. Always classify neutrally into `first-party`, `historical first-party`, `reseller`, `marketplace`, `third-party`, or `unknown`.
- **Conflicting Action Destinations (B-01):** Requires both an official action destination and an external action link (buy, signup, enroll, checkout) pointing to a non-official host. Verified social channels (`sameAs`) are excluded.
- **Potentially Stale Facts (B-02):** Preserves both official and external values, currency, sources, confidence, and timestamps. Reports "potentially stale or conflicting fact" without declaring either side fraudulent.
- **Entity Ambiguity (B-03):** Flags same-name entities on other domains that lack official anchors; explicitly framed as ambiguity rather than impersonation.
- **Official-Source Clarity (B-04):** Recommends adding explicit official-site declarations on primary pages when multiple public representations exist.
- **Outdated Platform Representation (B-05):** Flags historical platforms sharing identity anchors that remain active without migration notices or 301 redirects to the authoritative domain.
- **Insufficient Evidence:** If external evidence is ambiguous or absent, return no conflict rather than inventing findings.

## Scoring Separation

The reporting engine strictly separates identity dimensions:
1. **First-party Identity Confidence:** Measures how clearly the authoritative site declares and structures its own identity.
2. **Cross-web Identity Confidence:** Evaluates cross-web consistency. High only when external representations have been discovered, evaluated, and verified consistent. If no external sources were evaluated, defaults to 50 (reflecting uncertainty, not proof of perfection).
3. **Source Consistency:** Deducts points for conflicting destinations, stale prices, or unmigrated platforms.
4. **External Conflict Risk:** Escalates proportionally to the severity of detected cross-source conflicts (0 when consistent, high when critical destination or price conflicts exist).
5. **Overall AI Readiness:** Deterministic composite score across all audit pillars.

