---
name: brand-identity-audit
description: Audits whether people and AI systems can identify an official brand, its current authoritative destination, and conflicts with observed public representations. Use during a read-only public website audit.
license: MIT
compatibility: Requires normalized first-party pages and optional caller-supplied public-source observations. Never signs in, purchases, submits forms, or modifies a website.
---
# Brand Identity Audit

Use this specialist skill to compare the official site's organization, domain, contact and action-destination claims against bounded observed sources. It is generalized: a source may be a directory, reseller, old platform, profile, or another domain.

Report a conflict only when evidence identifies a material disagreement. A different source is not malicious by default; use neutral labels such as *stale*, *conflicting*, or *potentially unofficial*.

The audit creates question-to-fact simulations (for example, “What is the official website?”). These are an evidence framework, not a claim about an AI assistant's live answer. See [the detection checklist](references/detection-checklist.md) for evidence thresholds and exclusions.
