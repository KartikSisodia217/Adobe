# Detection checklist

## Evidence and exclusions

- Establish first-party authority from the audited hostname, canonical URL, Organization JSON-LD, visible official-source statements, and contact/action links.
- Compare only public observations explicitly supplied to the audit or outbound references discovered on the official site. Do not infer search rank, age, malice, ownership, or truth from mention count.
- A conflicting action destination needs both an official/current context and a different observed purchase, booking, signup, or contact destination. Verified social `sameAs` references are not conflicts.
- A stale fact finding preserves both values, sources, confidence, and any supplied timestamp. It says “potentially stale” rather than declaring either source wrong.
- Same-name identity ambiguity requires a matching name on another non-authoritative domain; it is not an impersonation finding.
- If there is insufficient external evidence, return no conflict rather than inventing a problem.

## Scoring

The fusion layer applies deterministic severity: an evidence-backed conflicting critical action destination is critical; conflicting material facts are high; ambiguity and missing official clarity are medium. Summary scores start at 100 and deduct published severity weights, so they summarize findings rather than replace them.
