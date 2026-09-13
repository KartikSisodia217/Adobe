---
name: brand-identity-audit
description: Audits whether people and AI systems can identify an official brand, its current authoritative destination, and conflicts with bounded observed public representations across the web.
license: MIT
compatibility: Uses bounded, read-only public discovery and caller-supplied observations. Never signs in, purchases, submits forms, or modifies a live site.
---
# Brand Identity & Cross-Web Conflicting Presence Audit

Use this specialist skill to compare the official site's organization, domain, canonical URL, contact details, prices, and action-destination claims against bounded external representations discovered across the web. It is generalized: an external representation may be a directory, authorized reseller, historical platform host, marketplace, social profile, or another domain.

### Source Classification Taxonomy
Every discovered source is evaluated and categorized using evidence-backed labels:
- **first-party:** Verified primary domain, canonical host, or verified official social profile (`sameAs`).
- **historical first-party:** Predecessor domain or hosted platform that shares verified brand identity anchors (same creator, matching brand name, shared social handles) but lacks redirection or explicit official delegation.
- **reseller:** Authorized partner or distributor offering products/services with explicit reseller affiliation.
- **marketplace:** Multi-brand directory or storefront (e.g., Udemy, Amazon, Coursera).
- **third-party:** External site reviewing, discussing, or referencing the brand.
- **unknown:** External source with insufficient evidence for high-confidence classification.

### Conflict Detectors
- **B-01 (Critical):** Conflicting Authoritative Destination — an external representation directs purchases, enrollments, or logins to a different non-official host.
- **B-02 (High):** Potentially Stale or Conflicting Fact — price or availability contradictions between official and external representations.
- **B-03 (Medium):** Same-Name Entity Ambiguity — another non-authoritative domain presents the entity name without verified identity anchors.
- **B-04 (Medium):** Official-Source Clarity Gap — missing explicit authoritative-site declaration when external representations or conflicts exist.
- **B-05 (High):** Outdated Platform Representation — an active historical first-party presence continues serving users without migration notices or redirects to the authoritative domain.

See [the detection checklist](references/detection-checklist.md) for evidence thresholds, classifications, and scoring separation.
