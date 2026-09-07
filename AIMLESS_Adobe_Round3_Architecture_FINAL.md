# AIMLESS - Adobe University Hackathon Round 3
## Final Architecture

**Decision:** Build a four-skill, read-only marketplace that produces a deliberately short report: confirmed defects first, then clearly labelled risk signals and proactive improvements. Do not implement a generic "AI readiness score."

## 1. Executive Summary

The current Opus architecture is a good precision-first foundation, but it should **not** be submitted unchanged. Its most important corrections to Gemini are sound: blocking a training crawler is not proof that real-time AI retrieval is blocked; missing `sameAs`, `llms.txt`, timestamps, ARIA attributes, or semantic elements is not by itself a defect; and a button's accessible name must be computed rather than inferred from the absence of `aria-label`.

However, Opus still has four material weaknesses:

1. Its fixed URL-regex selection will miss important pages on many unseen sites.
2. Its raw-versus-rendered comparison does not define an implementable test for *important* content.
3. Conditional browser use means it may skip the only evidence needed to assess on-site interaction barriers.
4. Its security design checks only the initially typed host and suggests `--no-sandbox`; neither is acceptable for an untrusted-site auditor.

The final design retains four skills, but changes their boundaries and execution. It discovers a small, adaptive representative sample; always opens a bounded rendered session for the landing page and (when present) one task page; reports only evidence-backed mechanism failures; treats metadata gaps as opportunities unless a demonstrable failure or contradiction exists; and uses one optional, tightly bounded Wikidata lookup only to corroborate unresolved entity ambiguity. General web search is not in the submission's critical path.

The intended answer to the ultimate test is **yes, with this final architecture**: on an arbitrary unseen public website, AIMLESS can reliably return a small number of high-confidence findings or an honest clean/limited-coverage result, without pretending it can measure actual traffic, rankings, model training, or user retention.

## 2. Adobe Requirements

The Adobe handout is authoritative. “Satisfies” below evaluates this final design, not a claim that Adobe explicitly mandates a particular detector.

| Adobe requirement | Exact requirement | Final architecture satisfies? | Evidence in design | Problem to avoid |
|---|---|---:|---|---|
| Marketplace package | Submit a single marketplace with one or more Agent Skills | Yes | Root `marketplace.json`, `skills/`, README | Do not submit a loose collection of scripts |
| One entrypoint | Exactly one designated entrypoint receives the audit request and emits the final report | Yes | `audit-orchestrator` is the only `entrypoint: true` item | No competing report writers |
| Skill composition | Skills may compose; focused decomposition is rewarded but a single well-built skill is accepted | Yes | Four non-overlapping responsibilities | Do not add cosmetic micro-skills |
| AI discoverability | Detect problems hurting why a brand is found or cited | Yes, within observable scope | Access, crawlability, extractability, facts, identity, contradictions | Do not claim ranking or citation outcomes AIMLESS cannot observe |
| On-site engagement | Detect why visitors who arrive do not stay | Yes, within observable scope | Task-blocking overlays, navigation/orientation, named controls, form barriers | Do not equate DOM style or all accessibility issues with retention |
| Evidence and severity | Each problem includes evidence and severity | Yes | Typed evidence objects, confidence gate, severity rubric | Do not turn absence of metadata into a serious finding |
| Suggested actions | What to change and how, prioritized; may include proactive improvements | Yes | Deterministic remediation templates with mechanism and verification | Do not use vague SEO advice |
| Single report schema | `site`, `audited_at`, severity summary, and finding id/title/severity/evidence/action are the minimum | Yes | Section 32 schema includes every required field | Keep required `evidence` as a human-readable summary too |
| Unseen-site generalization | Evaluation is on sites not supplied to teams | Yes | Adaptive page selection, type inference, no brand allowlists | Avoid URL-pattern-only logic |
| Read-only safety | Recommend-only; no site modifications | Yes | GET/HEAD only; browser aborts mutations and downloads | Never submit forms or invoke authenticated flows |
| Respect robots | Respect `robots.txt`; no rate abuse | Yes | Robots-aware sampler with limited public fetches | Robots is not an SSRF permission system |
| Runtime | Typical site audit under 5 minutes | Yes | 180 s target and 270 s hard stop | Do not wait unboundedly for `networkidle` |
| File size | Zip at most 50 MB, no pretrained weights | Yes | Source, rules, fixtures, and no browser binaries or models | Do not package Chromium/node_modules |
| Provider neutrality | Skills portable and tool needs declared | Yes | Standard SKILL.md, relative scripts, documented tool abstractions | Do not hardwire a proprietary agent API |

### Explicit scope boundary

An audit can observe public HTTP responses, DOM/accessible-tree state, and selected public knowledge-graph results. It cannot observe whether a particular assistant indexed a site, whether a model will cite it, real visitor bounce rate, hidden personalized content, authenticated flows, or the truth of arbitrary external claims. The report must say “retrieval risk,” “extractability risk,” or “interaction blocker,” not “ChatGPT will hallucinate” or “visitors will leave,” unless the observable mechanism itself blocks the task.

## 3. Design Principles

1. **Prove the mechanism, then report it.** A serious finding needs an observable condition and a plausible direct path to harm.
2. **Precision over coverage under uncertainty.** Suppress low-confidence negative claims. A coverage limitation is preferable to an invented defect.
3. **Representativeness over URL conventions.** Select pages from page roles and link structure, not `/blog` or `/pricing` alone.
4. **Separate facts from metadata.** Metadata can improve machine interpretation, but absence alone is normally an opportunity, not proof of failure.
5. **Use the least powerful method that works.** Deterministic parsing precedes browser execution; browser evidence precedes semantic synthesis; LLM output never decides a detector.
6. **Accessibility is evidence for interaction quality, not a proxy for engagement.** Report it as a serious engagement issue only when an observed control, dialog, navigation, or form task is blocked or materially ambiguous.
7. **Every action repairs the observed mechanism.** Recommendations name the affected element/fact and include a verification condition.
8. **Bound every external dependency.** The audit stays useful if a sitemap, browser, or Wikidata is unavailable.

## 4. Failure-Mode Taxonomy

| Classification | Meaning | Report treatment | Example |
|---|---|---|---|
| Confirmed defect | Direct evidence proves a crawler, extractor, or user/agent task is blocked, contradicted, or materially misleading | Finding; High or Critical if impact is broad/blocking | `robots.txt` denies all crawlable paths to a configured retrieval UA; a modal traps focus and has no reachable dismiss/continue control |
| Risk signal | Evidence exposes a plausible but unproved mechanism | Finding only if corroborated; normally Medium | A key visible price appears only after JS and no server-side equivalent is present |
| Optimization opportunity | A known improvement would strengthen an otherwise functioning site | Separate proactive suggestion, no defect count | Add valid Product JSON-LD where visible product facts already work in text |
| Unsupported | Evidence is absent, non-specific, or cannot establish the claimed outcome | Suppress | “DOM depth is 16”; “no llms.txt”; “multiple search hits exist” |

The audit's supported failure modes are deliberately narrow:

- **Access:** a public crawler with a configured retrieval identity is expressly denied all relevant public paths, or canonical URL handling makes sampled public pages unresolvable.
- **Machine extractability:** materially important site facts available after render are absent from raw HTML and no equivalent non-JS public representation is found.
- **Fact integrity:** first-party visible, JSON-LD, Open Graph, canonical, or date values contradict each other; or a generic identity remains unresolved after first-party identifiers and a bounded external corroboration check.
- **Interaction and orientation:** a visitor/agent cannot dismiss an interstitial, identify an essential control, reach a main route, or complete a minimal non-mutating task due to an observed interface barrier.

## 5. Independent Review: Gemini vs. Opus

| Area | Gemini proposal | Opus proposal | Which is better? | Final decision and reason |
|---|---|---|---|---|
| Skill decomposition | Five skills, including a small access/curation skill and separate entity skill | Four skills, better grouping | Opus | Keep four, but replace the content/identity boundaries with explicit fact-integrity responsibility |
| Retrieval access | Incorrectly treats several bot blocks as critical | Separates training from retrieval/search bots | Opus | Preserve distinction; report configured retrieval blocks as a risk/defect only with a broad path impact |
| `llms.txt` | Missing file is a detector | Proactive suggestion only | Opus | Preserve: no serious finding from absence |
| Rendering | Raw/rendered text ratio >50% | Important-content caveat but no concrete algorithm | Opus partially | Replace with role-aware fact fingerprints and an implementable comparison |
| Content semantics | DOM depth/div-soup and canvas/SVG broadly treated as defects | Narrows claims but leaves non-text detector vague | Opus partially | Remove depth/div count; inspect only key visible facts that lack machine-readable text alternatives |
| Entity resolution | Missing `sameAs` + multiple Wikidata results becomes High | Correctly adds generic-name condition | Opus | Strengthen: Wikidata search alone never proves ambiguity; first-party identity context must remain unresolved |
| Freshness | Uses loosely defined external/internally dated contradiction | Removes freshness as a detector | Neither alone | Restore only first-party contradiction and explicit past-dated claims; metadata absence stays a suggestion |
| Engagement | Equates missing ARIA labels with agent blindness | Computes accessible name and focuses dialogs/nav | Opus | Add bounded interaction-flow checks; preserve full accessible-name computation |
| Modal logic | Any nameless close target is a critical trap | Better but overstates AOM behavior and only checks close control | Opus partially | Require an active blocking modal plus failure of close/continue/escape/focus path |
| Page selection | Exactly four pages selected with URL regexes | 3-5 pages with URL regexes and nav fallback | Opus slightly | Replace with role, sitemap, internal-link, and content-cluster selection |
| External verification | Wikidata used for entity and “staleness” | Wikidata only | Opus | Keep Wikidata only for qualified identity ambiguity; no search in critical path |
| LLM use | Not sufficiently bounded | Evidence-only prose synthesis | Opus | Make it optional and validate its output against templates/schema |
| Evidence | String examples; broad assertions | Better evidence intent but not a typed model | Opus | Add selector, response, extracted value, expected condition, and capture timestamp fields |
| Confidence/severity | Deterministic equals high; “deleted” low findings | General stance, limited rules | Neither alone | Confidence measures evidence sufficiency; severity measures impact, independently |
| Testing | Four synthetic sites | Five sample scenarios | Neither alone | Build mutation fixtures, clean controls, real-site regression set, and measurable gates |
| Security | Initial private-host check and `--no-sandbox` | Simplified initial host check | Neither | Validate every DNS resolution and redirect destination; keep browser sandbox enabled |
| Marketplace compliance | Manifest contains unsupported extra conventions and malformed/ambiguous skill map example | Adobe-compatible list-style manifest | Opus | Use Adobe's list shape and current Agent Skills constraints |

### What Opus fixed correctly

- Training crawler access and real-time retrieval crawler access are different mechanisms.
- A real accessible name can come from visible text, not only ARIA attributes.
- Missing `sameAs` and missing `llms.txt` are not proof of failure.
- A single scalar readiness score creates unjustified precision.
- Conditional and bounded work is important to meeting the runtime budget.

### What to restore from Gemini

- A dedicated factual-integrity concern is worthwhile, but only for contradictions that AIMLESS can observe.
- Fixture-based evaluation must exist before submission; it is more valuable than adding another detector.
- Strict caps and explicit request interception are worth retaining, after correcting their implementation.

### Important wrong assumption in both proposals

Both assume that simple technical proxies can establish an AI outcome. They cannot. A crawler allow rule, JSON-LD, `sameAs`, or low raw-text volume can establish an input condition or risk; it does not establish indexing, citation, truth, or user retention. The final report separates these levels explicitly.

## 6. Detector Audit and Final Decisions

| Detector | Evidence strength | FP risk | FN risk | Generalization | Runtime | Verdict |
|---|---|---|---|---|---|---|
| D-01 retrieval bot access | Strong for a parsed explicit deny; moderate for downstream discoverability impact | Low if UA/path semantics are correctly parsed | Medium: access may fail outside robots | High | <1 s | MODIFY |
| D-02 structured-data absence/completeness | Weak for defect claim; strong for a validation error/contradiction | High if absence is reported | Medium | High | <2 s | MODIFY |
| D-02 schema-visible contradiction (“cloaking”) | Strong where same property/value conflicts are aligned to same page/entity | Medium: presentation can legitimately differ | Medium | Medium-high | <3 s | KEEP, narrow |
| D-03 entity ambiguity | Moderate only after first-party and external corroboration | High from name search alone | High for entities absent from Wikidata | Medium | 1-3 s | REPLACE |
| E-01 JavaScript rendering gap | Strong when a keyed fact is render-only | Medium without fact matching | Medium for lazy/personalized content | High | 25-75 s | REPLACE |
| E-02 non-text content trap | Strong when a key visual fact has no text/alt/label equivalent | Medium for decorative assets/charts | Medium | Medium | 2-5 s plus render | MODIFY |
| G-01 unnamed interactive control | Strong for an essential rendered control with empty computed name | Medium for icon-only familiar controls | Medium | High | 5-15 s | MODIFY |
| G-02 modal trap | Very strong only after observing an active blocking dialog and failed safe exits | Low with interaction test | Medium for timing/personalization | Medium-high | 10-20 s | REPLACE |
| G-03 navigation opacity | Weak from missing `<nav>` alone; strong from absent labelled route and task path | High with semantic-only rule | Medium | Medium | 5-20 s | REPLACE |

### D-01 - retrieval access

**Detects:** Explicit disallow rules that deny relevant public paths to a configured retrieval/search bot identity, plus site-wide `*` denial where no more-specific applicable allow overrides it.

**Evidence:** response URL/status/content of `robots.txt`; parsed matching group; normalized URL path; winning allow/disallow rule; configured UA category and registry version.

**What it proves:** the declared robots policy requests that the named crawler not fetch that path. It does not prove any provider's current crawler identity, indexing behavior, or citation outcome.

**Healthy false trigger:** an operator intentionally blocks a bot for legal or load reasons. That is still a real discoverability trade-off, so phrase it as “declared retrieval access restriction,” not an error.

**Broken-site evasion:** WAF, IP/geographic blocks, login walls, `noindex`, or bot-specific serving are out of scope unless observed. The system must not infer them.

**Final rule:** High if all sampled public canonical paths are denied to a retrieval UA; Medium if only a representative key path is denied; no finding for training-only blocks. Use a registry in `references/crawler-roles.json`, versioned and explainable, rather than hardcoded folk knowledge. If the registry lacks a verified retrieval role, output a coverage note rather than a finding.

### D-02 - structured facts and schema consistency

**Detects:** (a) invalid JSON-LD parse/schema graph errors, (b) same-page conflicts between a visible keyed fact and an asserted structured equivalent, and (c) a proactive opportunity to add schema where a repeated, high-value visible fact type has no structured representation.

**Evidence:** raw JSON-LD fragment and JSON pointer; selector and normalized visible value; property mapping; page canonical URL; parser/validator error.

**What it proves:** invalid markup or a concrete first-party inconsistency. It does **not** prove that lack of Product/Organization/Article schema prevents extraction.

**Healthy false trigger:** an article author date differs from a company copyright footer; a marketing price excludes tax while a structured offer includes it; a localized name differs. Compare only matched entities/properties, normalize units/currency/date granularity, and otherwise label as “needs review.”

**Final rule:** report a High factual-integrity defect only for material same-entity conflicts such as different product price/currency/availability, organization name/address/contact, or page title/date after normalization. A malformed JSON-LD item is Medium if the site relies on it for an otherwise absent machine-readable fact; otherwise a Low/Medium technical opportunity. Absence is proactive only.

### D-03 - entity ambiguity

**Detects:** A first-party identity that remains ambiguous despite its own identity evidence.

**Evidence:** extracted Organization/LocalBusiness identity fields (`name`, URL, logo, address, telephone, `sameAs`, parent/brand); page title; canonical hostname; two or more candidate Wikidata results with labels/descriptions/IDs; a deterministic mismatch/unresolved decision record.

**What it proves:** only that AIMLESS cannot confidently bind a generic public identity to one candidate using available evidence. It does not prove that assistants confuse the entity.

**Healthy false trigger:** “Delta” with a clear address, official domain, logo, and consistent Organization schema but no Wikidata link. Multiple Wikidata results are merely candidates.

**Broken-site evasion:** a unique but unknown entity absent from Wikidata; a malicious `sameAs`; entity signals hidden behind login. Do not report an external absence as a defect.

**Final rule:** use Wikidata only when the name is generic/short or first-party fields conflict. Bind a candidate only if at least two independent first-party attributes match it (for example official domain plus locality, or an explicit QID URL). If two credible candidates remain and the site exposes no canonical identity anchoring, report **Medium risk signal**, not High defect. Recommend an Organization graph with official URL, address/area where applicable, logo, and verified public profile/knowledge-graph links. If direct identity evidence is already unambiguous, suppress regardless of search results.

### E-01 - important-content rendering gap

**Detects:** Important first-party facts that are present in a stable rendered state but missing from the initial HTTP HTML and no equivalent is found in raw text, JSON-LD, meta tags, `<noscript>`, or linked alternate page.

**Evidence:** page role; fact fingerprint (type, normalized value, selector, contextual heading); raw source search result; rendered selector/text; capture time; render state and timeout.

**What it proves:** a simple fetcher cannot obtain that observed fact from initial HTML. It does not prove all crawlers fail, because some render JavaScript.

**Healthy false trigger:** cookie notices, personalized greetings, analytics counters, timestamps, recommendations, animation, or a JavaScript change in wording. These are excluded by the fact classifier.

**Broken-site evasion:** content hidden behind interaction/personalization or delayed beyond timeout. Report coverage limitations, not a failed result.

**Final algorithm:**

1. Infer the page role and collect candidate facts only from `main`, `article`, product/offer structured regions, page H1, key CTA/navigation, and Organization contact/footer block.
2. In rendered DOM, derive normalized fingerprints for: organization name; page H1/title; article headline/byline/date; product/service name, price, availability and primary CTA; contact/location; and primary navigation labels. Do not harvest arbitrary text length.
3. For each candidate, search raw DOM-visible text, JSON-LD, relevant Open Graph/meta tags, `<noscript>`, and an HTTP `Link rel=alternate` target. Match exact normalized text, structured equivalent, or an entity-property equivalent.
4. A candidate is render-only only when no equivalent exists. Ignore candidates under 3 meaningful tokens except price/contact values and exclude consent/advertising/personalized regions.
5. Report Medium when a core content fact on the landing, article, or conversion page is render-only; High only when the sample shows the site’s primary identity/content and key task fact are all render-only on every available fallback. Recommend SSR, static pre-rendering, or a truthful `<noscript>`/HTML equivalent, not removal of JavaScript.

### E-02 - non-text-only facts

**Detects:** A key fact used for identity, task choice, or content understanding that appears visually in image/canvas/SVG but lacks a text alternative or a nearby/repeated text/structured equivalent.

**Evidence:** element selector, asset type, accessible name/alt, OCR-free textual DOM checks, adjacent label/figcaption, and observed rendered context.

**What it proves:** the fact is not programmatically exposed in the observed representation. Canvas presence, an SVG, or an image with empty `alt` alone proves nothing about whether it carries essential content.

**Final rule:** inspect only visually prominent candidates in primary content or essential task controls; never OCR by default. Flag Medium only if a human-inspectable visual fact is needed to distinguish the page/product/action and no machine-readable equivalent appears. Decorative imagery is ignored.

### G-01 - essential unnamed controls

**Detects:** An essential rendered interactive control whose computed accessible name is empty or misleading enough that a user/agent cannot determine its action.

**Evidence:** browser accessibility snapshot, DOM selector, HTML snippet, role, computed name, bounding box/visibility, associated form or modal context.

**What it proves:** the exposed accessibility tree lacks a usable name, not that every visitor will abandon the page.

**Healthy false trigger:** an icon-only close button named by visually-hidden text or `aria-labelledby`; a harmless decorative control. Use browser-computed name, not attribute presence; test only essential controls.

**Final rule:** Medium for one essential nameless control (primary CTA, menu trigger, search, form submit, dialog action); High only if it prevents the only observed path past an active blocker. Do not flag generic links/buttons outside a sampled task path.

### G-02 - blocking modal/interstitial

**Detects:** An active modal/overlay that blocks interaction with primary content and cannot be dismissed or progressed through by a safe, observable keyboard/accessible-control path.

**Evidence:** screenshot/DOM state; accessibility tree; overlay geometry and pointer interception; focused element; attempt log for Escape, visible labelled close, declared continue/reject, and Tab cycle; URL/state after each safe action.

**What it proves:** a task blocker in the captured public state. A role, z-index, or non-native close element alone does not prove a trap.

**Final rule:** open a fresh context. Without entering data, try Escape, a clearly labelled close/reject/continue action, and keyboard Tab for at most 8 focus changes. A Critical finding requires the overlay to cover/intercept the primary route and all safe exits to fail while focus is trapped/obscured. A Medium finding covers a usable but unnamed close control or non-blocking dialog semantics issue. Cookie consent must not be treated as a defect merely because it requires a choice; it is a defect only if it prevents continued browsing with no accessible path.

### G-03 - orientation and navigation task path

**Detects:** A public landing page that lacks an observable route to its main content/task, or an observed navigation control that cannot be identified/operated in the accessibility tree.

**Evidence:** inferred page goal; H1/landmark tree; primary navigation/control names; link targets/status; bounded keyboard/activation trace.

**What it proves:** a specific route is blocked or opaque in the sampled state. The absence of a `<nav>` landmark or a visual-only judgment does not prove poor engagement.

**Final rule:** infer one non-mutating route: read an article, open product/service detail, find contact/location, or reach documentation. Test at most one from the landing page. Report Medium when the route is visibly offered but unnamed/unreachable or its target fails; report no defect where a custom but usable navigation scheme works. Do not diagnose “excessive friction” from subjective design taste.

## 7. Architecture Overview

```text
input URL
  -> safe canonicalization and DNS/redirect gate
  -> robots policy + homepage fetch
  -> adaptive candidate graph and representative sample
  -> concurrent raw fetch/parse across <= 6 pages
  -> one sandboxed browser context on landing + <= 2 representative pages
  -> access/content, fact-integrity, and engagement analyses
  -> evidence normalization, deduplication, causal cross-signal rules
  -> confidence gate, severity assignment, deterministic recommendations
  -> one Adobe-compliant JSON report
```

### Final skill decomposition - 4 skills

| Skill | Responsibility | It owns | It must not own |
|---|---|---|---|
| `audit-orchestrator` (entrypoint) | Safe audit lifecycle and final composition | URL guard, budgets, sample plan, cross-signal validation, report schema | Detector-specific interpretation |
| `access-content-auditor` | Public retrieval and machine-readable first-party content | robots parsing, HTTP/canonical checks, raw parsing, structured-data parse, render-only fact comparison | Entity identity judgement, interaction flow |
| `fact-integrity-auditor` | First-party identity and factual consistency | identity graph, normalized field comparison, qualified Wikidata corroboration, date/fact conflicts | Broad web search, claims of external truth |
| `engagement-auditor` | Bounded public on-site task accessibility/orientation | accessibility tree, essential controls, modal exits, one route test | Aesthetic UX scores or conversion-rate assertions |

Each skill returns typed candidate findings and coverage notes. Only the orchestrator emits the public report. This is meaningful composition: network/content evidence is independent of entity consistency, and both are independent of browser interaction behaviour.

## 8. End-to-End Execution

1. **Validate input (0-8 s).** Accept only `https:` by default; normalize host, strip fragments, resolve DNS, and reject unsafe destinations before each connection.
2. **Fetch root and policy (parallel, 3-15 s).** Fetch `robots.txt`, homepage, and sitemap candidates with safe GET requests. Record all failures as coverage, not defects unless they are public-site access failures.
3. **Discover and score candidates (10-25 s).** Construct a candidate graph from sitemap(s), canonical links, homepage links, and one shallow internal-link expansion. Infer page roles and select a diverse sample.
4. **Raw pass (20-45 s).** Concurrently fetch at most six canonical pages on the same origin. Parse headers, canonical/hreflang, titles, landmarks, facts, JSON-LD, and safe text.
5. **Rendered pass (35-115 s).** Start one sandboxed browser context. Render landing page and up to two high-value pages selected after raw analysis. Capture DOM, accessibility tree, screenshots only for reportable interaction evidence, and fact fingerprints. Never use unbounded `networkidle`.
6. **Auditor pass (45-135 s).** Run the three auditors independently over normalized snapshots. Wikidata is invoked only after a qualifying unresolved identity decision.
7. **Fusion and synthesis (125-160 s).** Deduplicate page instances, apply confidence/severity rules, cap findings, create deterministic actions, and validate the final JSON.
8. **Fail-safe output (by 180 s target; 270 s absolute stop).** Return valid report plus coverage notes even if rendering/external lookup timed out.

## 9. Page Selection

Hard-coded path regexes are useful hints, not selection logic. AIMLESS must work for an ecommerce shop, university, government portal, restaurant, news site, portfolio, nonprofit, documentation site, or marketplace.

### Candidate sources and caps

- Root canonical page: always include.
- `sitemap.xml`, sitemap index entries, and robots sitemap declarations: parse at most 3 sitemap documents and 2,000 URLs, preserving `lastmod` only as a ranking hint.
- Homepage same-origin links: parse up to 120 unique canonical candidates.
- One shallow expansion from the top 12 same-origin links: up to 60 more candidates.
- Never fetch unauthenticated URLs with credentials, tracking parameters, destructive-looking paths, or non-HTTP schemes. Never submit a form to discover pages.

### Role inference

Assign transparent features rather than deterministic URL categories:

| Role | Signals | Selection objective |
|---|---|---|
| Landing / identity | root, Organization facts, highest internal-link centrality | Brand identity, primary navigation, access |
| Detail / conversion | visible Offer/Product/Service schema, price, action CTA, repeated card target, or commercially meaningful title | Key facts and one task path |
| Editorial / information | `Article`, `<article>`, date/byline, long main content, documentation headings | Extractability and factual dates |
| About / contact / location | contact details, Organization/LocalBusiness, map/address, “team” semantics | Identity binding and contact facts |
| Index / category | high out-degree collections, breadcrumbs, feed/category markup | Crawlability and route traversal |

Rank candidates by role diversity, same-origin link centrality, content richness, canonical uniqueness, and privacy-safe status. Down-rank search results, cart/account/checkout, calendar/booking, infinite faceted URLs, files, language duplicates, and query variants.

### Final sample

Fetch raw snapshots of up to six pages: landing plus up to one each of detail/conversion, editorial, about/contact, index, and an additional high-centrality page. Render at most three: landing, the highest-value content/detail page, and one page needed to resolve a raw render risk. If a role does not exist, do not fabricate one. Emit `coverage.page_roles_sampled` and `coverage.not_observed_roles`.

## 10. Crawl Strategy

- Respect parsed `robots.txt` for the audit user agent before voluntary crawling beyond the root; report declared retrieval rules separately from the auditor’s own policy.
- Use same-origin GET requests only, HTTP redirects limited to five, and a per-host token bucket of 1 request/second with concurrency 3 (never more than 6 outstanding requests).
- Cap raw response size at 2 MB compressed / 8 MB decompressed; cap HTML parse nodes/text; stop reading after bounds. Record truncation.
- Send clear `User-Agent: AIMLESS-Audit/1.0 (+contact URL)` and Accept headers; never masquerade as a search or AI crawler.
- Preserve response URL, status, canonical/header data, and timestamp. Normalize URL fragments and safe query parameters only for deduplication, retaining the original evidence URL.
- HEAD is optional and never used as an authority over GET because servers frequently differ; no OPTIONS, POST, PUT, PATCH, DELETE, or form submission.

## 11. Rendering Strategy

Opus’s “skip rendering if raw text exceeds 1,000 characters” rule is unsafe: a long SSR shell can conceal the only relevant conversion information, and engagement evidence exists only in a rendered interaction state.

### Browser protocol

- Start **one** Playwright/Chromium context with a fresh profile; preserve the browser sandbox and use OS/container isolation. Do not pass `--no-sandbox`.
- Navigate only to already safety-approved same-origin URLs. Route interception allows document, stylesheet, script, and essential XHR/fetch from approved public origins; abort media, downloads, websocket/eventsource, third-party analytics/ads, popups, and all mutating method requests.
- Wait for `domcontentloaded`, then a bounded 1.5 s quiet window and maximum 10 s navigation/page. Do not wait for global `networkidle`.
- Disable permission prompts; deny geolocation/camera/microphone/notifications; no stored credentials; no downloads; no clipboard access.
- Capture `document.documentElement.outerHTML` within a 1.5 MB cap, visible text, landmark/accessibility snapshot, and stable screenshot only where it substantiates an interaction blocker.
- Use a new page/context for modal testing so consent/popup state cannot contaminate fact extraction. No user text is typed; no forms are submitted.

### Hydration and JavaScript classification

Classify each page’s **important facts**, not total text:

| Outcome | Rule | Report treatment |
|---|---|---|
| Raw available | Fact is in raw visible text, JSON-LD/meta, `noscript`, or equivalent linked HTML | No render gap |
| Render-enhanced | Raw equivalent exists but rendered form adds formatting or incidental dynamic text | No finding |
| Render-only risk | Core page-role fact appears after render but no raw equivalent exists | Medium risk signal |
| Site-wide render-only | Identity and central task/content facts are render-only across all applicable sampled pages and no fallback is observed | High defect/risk, with limitation wording |
| Indeterminate | Render failed, timed out, content personalized, or fact could not be classified | Coverage note only |

## 12. Content Extractability

The extractor builds a page snapshot, not a “semantic score.” It should collect:

- HTTP status/content type/headers, final URL, canonical link and robots meta.
- Main candidate (`main`, `article`, `[role=main]`, or readable-content heuristic), heading hierarchy, navigation landmarks, visible text, and text alternatives.
- JSON-LD, microdata/RDFa, Open Graph, and `meta` values with parser errors retained.
- Typed fact candidates: organization, service/product, article, contact/location, price/availability, date, primary CTA, and navigation labels.

### Machine-readable fact rule

A fact is considered available to a basic machine reader if it has a clear equivalent in initial HTML text, a truthful structured representation, an appropriate alt/accessible name, or an equivalent linked public HTML page. Structured data is supplemental, not a requirement. A page with clean raw text and no schema is not defective.

## 13. Entity Resolution

1. Extract first-party identity from Organization/LocalBusiness schemas, `og:site_name`, H1/title, footer/contact details, canonical hostname, and official linked profiles.
2. Normalize company/brand names, URLs, phone/address/locality, but keep raw values and provenance.
3. If identity is internally consistent and domain/locality/profile cues identify one organization, stop. Missing `sameAs` is at most a proactive improvement.
4. Only if the name is generic, contradictory, or lacks enough first-party anchors, issue one Wikidata `wbsearchentities` request with 3 s timeout and at most five candidates.
5. Treat results as candidates. Resolve only with two independent first-party matches or an explicit canonical link/QID. Never infer a match from label alone.
6. If ambiguity remains, report “identity anchoring is insufficient for unambiguous external binding” as Medium risk, with candidates listed as evidence. Do not claim misattribution actually occurs.

Use `sameAs` only for verified official URLs. A fabricated or unrelated link is worse than no link.

## 14. Freshness and Conflict Detection

Freshness deserves a narrow place in the system because the brief’s Round 2 context includes stale/misrepresented information, but a website-only audit cannot establish whether a fact is current in the world.

### Reportable cases

| Condition | Classification | Severity | Evidence |
|---|---|---|---|
| No `dateModified`, no Last-Modified, or generic copyright | Opportunity / unsupported | None | Do not create finding |
| Last-Modified differs from on-page date | Weak evidence only | None by itself | Header semantics are unreliable |
| Same page/entity asserts conflicting material dates/status/prices in visible text and JSON-LD | Confirmed integrity defect | Medium or High | Exact values and selectors/pointers |
| Page says a time-bounded event/offer is active while its explicit end date has passed at audit time | Confirmed stale first-party claim | High if conversion/availability is affected; otherwise Medium | Source text, timezone assumption, timestamp |
| Multiple first-party canonical pages make incompatible current claims about same named product/service | Confirmed conflict | High if a choice/transaction is affected | Both URLs, matched entity/fact |

No general search is required to establish those conditions. AIMLESS does not label a truth disagreement with a third-party page as “stale”; it can only say the site and external source disagree, and external source authority is usually unknowable in the audit.

## 15. AI Discoverability

| Mechanism | AIMLESS can observe? | Audit rule |
|---|---:|---|
| Robots policy for declared UA | Yes | Parse exact applicable rules and paths; distinguish retrieval role from training role |
| Actual crawler access/WAF/IP blocking | Partly | Observe only the auditor’s request; do not generalize |
| Search index/citation/model usage | No | Never claim it |
| Initial HTML crawlability | Yes | Record public status, canonical, robots meta, raw important facts |
| Rendered content | Yes, sampled public state | Compare typed facts, not text volume |
| Structured data | Yes | Parse/validate/compare, not mandate |
| Canonicalization | Yes | Identify broken/contradictory canonical references within sampled pages |
| Entity identity | Partly | First-party anchors plus optional candidate corroboration |
| Extractable facts | Yes | Assess typed raw/alternative availability |
| Conflicting first-party information | Yes, sampled facts | Report material normalized contradictions |
| Freshness in the real world | No | Report explicit expired claims/first-party conflicts only |
| `llms.txt` | Yes | Optional discovery artifact; proactive suggestion only |

`llms.txt` is not a broadly mandated retrieval standard. Its presence, validity, or absence never increases severity. Offer it only as a clearly optional documentation/navigation enhancement for documentation-heavy sites, after core blockers are resolved.

## 16. On-Site Engagement

The brief requires engagement, but AIMLESS has no analytics and must not manufacture a bounce-rate explanation. It can report the following defensible mechanisms:

| Defensible report | Observable test | Non-claim |
|---|---|---|
| A blocking overlay cannot be dismissed/progressed | Interception, focus, Escape/button/Tab trace | Not “all visitors will leave” |
| Essential control is unnamed/inoperable | Accessibility tree plus bounded activation check | Not “the site is inaccessible everywhere” |
| Primary public route cannot be found/reached | Inferred goal, labelled control/link, target status/trace | Not “navigation looks ugly” |
| Essential form cannot be understood before submission | Required input has no accessible label/instructions/error association | Not “form conversion is low” |
| Visible action leads to broken public destination | Safe GET/activation has 4xx/5xx or same-page failure | Not “the product is bad” |

The audit never diagnoses visual hierarchy, trust, persuasion, loading feeling, “too many divs,” or broad accessibility compliance as engagement defects without a concrete task mechanism. It may attach an advisory note that a broader UX/accessibility review is outside the bounded audit.

## 17. External Verification

**Final decision: do not use general web search in the core audit.** Search result ranking, regionalization, bot resistance, source quality, and latency add too much variability for too little proof. It would encourage the system to call every disagreement “stale” or every search result an identity match.

**Allowed external stage:** one optional Wikidata query for unresolved identity only. It is bounded (one request, 3 s timeout, five candidates), non-authoritative, and cannot alone create a High finding. Cache by normalized name within a run. If unavailable, entity ambiguity becomes indeterminate/proactive, not an error.

An optional post-hackathon expansion could use 1-3 source-quality-constrained searches for an explicit customer-approved fact-validation mode. It must be a separate mode because it changes scope, authority assumptions, and runtime; it is not part of the submission architecture.

## 18. Cross-Signal Validation

Cross-signal fusion must combine evidence about the **same mechanism**, not add unrelated weak facts.

### Causal fusion rules

| Candidate | Required independent corroboration | Final outcome |
|---|---|---|
| Retrieval restriction | Parsed winning deny + affected representative public path + configured retrieval role | Medium/High access finding |
| JS-only important content | Rendered core fact + failed raw/structured/noscript equivalent search | Medium render-only finding |
| Site-wide JS dependency | Render-only identity/primary fact across >=2 applicable sampled roles + no fallback | High finding |
| Structured contradiction | Same normalized entity/property in visible and structured facts, values materially incompatible | Medium/High integrity finding |
| Entity ambiguity | Generic/underspecified first-party identity + >=2 credible candidates after first-party matching fails | Medium risk signal |
| Blocking modal | Active overlay + primary-content interception + failed safe exit test | Critical blocker |
| Navigation blocker | Inferred primary route + no usable named route/control or observed failed target | Medium engagement finding |

Never elevate these combinations: missing schema + missing `sameAs`; deep DOM + no `<nav>`; missing last-modified + old copyright; missing llms.txt + any other metadata gap. They are not causally sufficient.

### Finding cap and deduplication

Deduplicate by `(mechanism, normalized affected entity, canonical URL cluster)`. Keep the strongest evidence instance and list additional impacted URLs. Cap output at 8 findings: all confirmed Critical/High first, then at most three Medium risk signals, then at most three proactive opportunities. If no finding qualifies, return zero serious findings plus coverage and optional improvements.

## 19. Evidence Model

Every finding contains a human-readable `evidence` string required by Adobe and a structured `evidence_items` array for inspection.

```json
{
  "kind": "dom|http|robots|structured_data|accessibility|interaction|external|comparison",
  "source_url": "https://example.com/pricing",
  "captured_at": "2026-08-28T10:20:30Z",
  "detector": "rendered_fact_gap_v1",
  "selector": "main .price",
  "node": {"tag": "span", "role": null, "accessible_name": ""},
  "observed": {"value": "$49/month", "representation": "rendered_text"},
  "expected_condition": "An equivalent price is available in initial HTML, structured data, noscript, or a linked public HTML alternative.",
  "comparison": {"raw_html_match": false, "json_ld_match": false, "noscript_match": false},
  "http": {"status": 200, "final_url": "https://example.com/pricing", "headers": {"content-type": "text/html"}},
  "artifact_hash": "sha256:...",
  "redactions": []
}
```

Evidence rules:

- Store bounded fragments, normalized values, and SHA-256 hashes; avoid whole pages and any typed/sensitive data.
- For robots, include the applicable user-agent group, winning path rule, and source response.
- For JSON-LD, use JSON Pointer and a redacted compact fragment.
- For accessibility, include browser-computed role/name plus matching selector; no claim based solely on a hand-rolled approximation.
- For interaction, include the ordered safe actions and their observed outcome. Screenshots are optional, never the only evidence.
- For external candidates, preserve query, endpoint, candidate ID/label/description, timestamp, and the first-party attributes that did/did not match.

## 20. Confidence Model

Confidence measures the sufficiency and reproducibility of evidence, not the team’s intuition or the severity of impact.

| Confidence | Exact rule | Publication rule |
|---|---|---|
| High | Direct deterministic evidence from a successful capture; expected condition is unambiguous; all required corroborating signals passed; no material contradictory evidence | Publish as confirmed defect if severity warrants |
| Medium | Strong primary evidence but a bounded assumption, incomplete coverage, or non-authoritative external corroboration remains | Publish only as a clearly labelled risk signal or non-blocking defect |
| Low | Heuristic pattern, partial page state, missing render, external search result alone, or uncertain fact/entity alignment | Suppress from findings; optionally use internally for future testing |

Serious findings require High confidence. A Medium-confidence issue may be shown only at Medium severity or below and must use cautious language (“may reduce,” “identity remains insufficiently anchored”). Low confidence never appears in the public findings list.

## 21. Severity Model

Severity measures scope, immediate task/retrieval impact, recoverability, and whether the mechanism affects a core site function. It never measures predicted model behaviour.

| Severity | Concrete threshold | Example |
|---|---|---|
| Critical | A public user/agent cannot continue a primary route in the sampled state, or an all-site access policy blocks every sampled path for a configured retrieval crawler | Modal intercepts page, focus/escape/close/continue all fail; global applicable deny to retrieval UA |
| High | A broad core identity/content/task mechanism is unavailable or materially contradictory across applicable sample pages | Landing identity and core offer facts are render-only with no fallback; same product’s current price conflicts on canonical pages |
| Medium | A localized but real access, integrity, or task usability defect; or a corroborated risk without proof of outcome | One key page denied; key submit/menu control has no computed name; entity remains ambiguous |
| Low | A limited technical issue whose impact is clear but not material | Invalid non-critical JSON-LD item where raw text is complete |

Proactive suggestions have a `priority` (high/medium/low) but no severity and do not inflate findings counts.

## 22. Recommendation Engine

Recommendations are deterministic templates keyed by detector and evidence. Each serious finding must answer:

1. **What is wrong?** Exact observed condition and affected page/entity.
2. **Why it matters?** The direct mechanism, scoped to what evidence supports.
3. **What to change?** File/markup/configuration-level action with an example where safe.
4. **Why it helps and how to verify?** Observable success condition.

| Detector | Recommended action pattern |
|---|---|
| Retrieval restriction | Review the matching `robots.txt` group; if retrieval is desired, add a more-specific allow rule for the intended public paths while retaining training-bot policy; verify with the same parser/path matrix |
| Render-only core fact | Render the fact in initial HTML via SSR/SSG/pre-rendering, or provide a truthful maintained non-JS HTML equivalent; verify raw GET contains the fact |
| Fact conflict | Choose one source of truth; generate visible content and JSON-LD from the same data field; verify normalized values agree on canonical pages |
| Identity risk | Publish consistent Organization information (official URL, legal/brand name, locality/contact where applicable) and link only verified official profiles/knowledge identifiers; verify two anchors resolve the entity |
| Modal trap | Use `<dialog>` or `role=dialog` with an accessible labelled close/continue action, initial focus, focus return, Escape behaviour where appropriate, and no background pointer interception after close; verify safe exit trace |
| Essential unnamed control | Use native `<button>`/`<a>` where appropriate and provide visible text or an accurate accessible name; verify browser accessibility snapshot |
| Route blocker | Provide a named, keyboard-operable link/button to the public route and repair the target; verify navigation trace/status |

The action generator does not invoke an LLM for these cases. It includes code only as illustrative, never applies a change. Avoid generic “improve SEO,” “add more keywords,” “use ARIA everywhere,” or “add llms.txt to fix AI visibility.”

## 23. LLM Usage

The submission can work with **zero LLM calls**. That is the preferred default.

If the host agent benefits from a short executive summary, make one optional evidence-grounded call after deterministic report generation:

| Field | Rule |
|---|---|
| Purpose | Rewrite already-approved findings into a three-sentence non-technical summary; never detect, rank, or add facts |
| Input | Final validated JSON minus HTML, screenshots, headers, and external raw payloads |
| Output | `summary.narrative` only, maximum 90 words |
| Token budget | 500 input / 120 output tokens |
| Grounding | Every assertion must cite a finding ID; JSON schema rejects uncited claims |
| Validation | Sentence-level check: entity/page/mechanism must be a substring/paraphrase of an approved finding; otherwise discard |
| Timeout | 5 seconds, one attempt |
| Fallback | Deterministic template: count by severity plus top two finding titles |

No LLM receives raw HTML or makes URL/page-selection, entity-resolution, severity, confidence, or remediation decisions.

## 24. Testing and Benchmarking

### A. Clean controls

Build fixtures that should yield **zero serious findings**:

| Test ID | Clean site | Expected result |
|---|---|---|
| C-01 | SSR ecommerce with readable product text, valid optional schema, keyboard-safe modal | 0 serious findings |
| C-02 | JS-rich app with complete SSR initial content and dynamic analytics only | 0 rendering findings |
| C-03 | Unique small business with no `sameAs` but domain/address/phone consistent | 0 entity findings; optional identity suggestion allowed |
| C-04 | Documentation site without `llms.txt`, complete raw text and canonical links | 0 discoverability defects |
| C-05 | Accessible custom controls with correct roles/names/keyboard support | 0 interaction findings |

### B. Controlled broken sites

Fixtures contain one independently asserted defect per initial test so a failure is diagnosable.

| Test ID | Injected defect | Expected finding | Severity | Required evidence | Expected remediation |
|---|---|---|---|---|---|
| B-01 | Retrieval UA denied `/` in robots | Declared retrieval access restriction | High | Parsed group, rule, sampled paths | Narrow allow rule if retrieval desired |
| B-02 | Core product name/price only inserted after JS | Render-only core product fact | Medium | Rendered fingerprint and failed raw alternatives | SSR/pre-render/equivalent HTML |
| B-03 | All landing identity/primary CTA facts only JS | Site-wide render-only core facts | High | >=2 typed fact failures | SSR/SSG or maintained fallback |
| B-04 | Image-only primary product comparison with no equivalent | Essential non-text fact unavailable | Medium | Selector/context/no alt/near text | Text table/alt/caption/structured equivalent |
| B-05 | Visible price `$49`, Product JSON-LD `$59` same SKU | First-party price conflict | High | Both values and entity match | Single source of truth |
| B-06 | Generic brand + two plausible candidates, no official anchors | Identity anchoring risk | Medium | First-party lack + candidates | Organization anchors/verified links |
| B-07 | Page advertises active offer ending yesterday | Expired first-party offer | High | Text/end date/audit time | Remove/update offer and feeds |
| B-08 | Blocking overlay has no reachable close/continue/escape | Blocking modal trap | Critical | Interaction trace/focus/interception | Accessible exit and focus management |
| B-09 | Essential menu/search button has empty computed name | Unnamed essential control | Medium | A11y node and selector | Native control/accurate name |
| B-10 | Primary contact route link is keyboard-inoperable/404 | Public route blocker | Medium | Trace/target status | Named operable link and fixed destination |
| B-11 | Invalid JSON-LD for otherwise raw-readable product | Structured data implementation issue | Low | Validator error/pointer | Correct JSON-LD syntax/property |
| B-12 | Same canonical service pages claim incompatible current hours | First-party fact conflict | Medium | Both canonical URLs/normalized facts | Centralize hours data |

### Measurement gates

For each fixture, assert finding ID, classification, maximum/minimum severity, required evidence kinds, and action mechanism. Measure:

- **Precision:** `TP / (TP + FP)` for reportable findings. Target >= 0.90 overall and >= 0.95 for High/Critical.
- **Recall:** `TP / (TP + FN)` by supported defect class. Do not report an aggregate that hides a weak modality.
- **False-positive rate:** clean pages/sites with one or more serious findings divided by all clean pages/sites. Target <= 5% per clean fixture family.
- **False-negative rate:** seeded defects missed divided by seeded defects, per detector.
- **Evidence correctness:** blind reviewer agrees that evidence supports the stated condition / reviewed findings. Target >= 0.95.
- **Recommendation correctness:** reviewer agrees the action repairs the stated mechanism / reviewed actions. Target >= 0.90.
- **Budget compliance:** p50/p95 runtime, total requests, rendered pages, external calls, and archive size.

### Unseen real-site evaluation

Maintain a versioned, consent-safe regression set of 20+ public sites across the page-role families. Do not tune rules on the hidden evaluation set. Two reviewers independently label only observable conditions from captured artifacts; adjudicate disagreements and record “not observable.” Run fixtures and real-site regression after every rule change. A good result is often “no serious finding with limited coverage,” not a long issue list.

## 25. Adversarial Testing

| # | Scenario | What AIMLESS should report | Final design correct? |
|---:|---|---|---:|
| 1 | Huge DOM, excellent landmarks/accessibility | Nothing about DOM size/depth | Yes |
| 2 | Small DOM, poor semantics but usable named routes | Nothing solely from semantics | Yes |
| 3 | No `sameAs`, uniquely identified company | No entity defect; optional suggestion only | Yes |
| 4 | Many Wikidata matches, obvious official domain/address | No entity risk | Yes |
| 5 | No `llms.txt`, excellent raw readable docs | No defect; optional doc suggestion at most | Yes |
| 6 | No Last-Modified, current page | No freshness finding | Yes |
| 7 | Perfect SSR SPA | No render gap | Yes |
| 8 | JS-heavy page where only analytics change | No render gap | Yes |
| 9 | Accessible modal with labelled close and Escape | No modal finding | Yes |
| 10 | Modal with visible labelled close and usable keyboard path | No trap finding | Yes |
| 11 | Modal close is inaccessible and all exits fail | Critical blocking modal | Yes |
| 12 | Ecommerce site with no statistics | No content finding | Yes |
| 13 | Article with no quotations | No content finding | Yes |
| 14 | Generic company name plus rich Organization anchors | No entity risk | Yes |
| 15 | Unique company absent from Wikidata | No entity defect | Yes |
| 16 | No sitemap, usable internal navigation | Coverage note only, no defect | Yes |
| 17 | Incomplete sitemap, representative nav exposes content | No sitemap defect; sample available pages | Yes |
| 18 | Thousands of pages | Sample/cap coverage note; no exhaustive claim | Yes |
| 19 | No product pages | Select other roles; no missing-product claim | Yes |
| 20 | PDF-heavy site with linked readable PDFs | Coverage note; no HTML extractability claim for PDF content unless PDF mode exists | Yes |
| 21 | Shadow DOM with accessible named control | Use rendered/a11y snapshot; no false positive | Yes |
| 22 | Lazy-loaded article body appears after bounded scroll | If core text appears only after safe bounded scroll and no raw equivalent, render-only risk; otherwise coverage note | Yes |
| 23 | Personalization changes prices/content | Do not compare personalized state as general truth; mark indeterminate | Yes |
| 24 | Cookie banner allows reject/continue | No modal trap | Yes |
| 25 | External page conflicts but first-party facts consistent | No stale/conflict finding | Yes |
| 26 | First-party JSON-LD conflicts with visible content | Material factual-integrity finding | Yes |
| 27 | Visual navigation lacks `<nav>` but links are named/operable | No navigation defect | Yes |
| 28 | Custom button has correct role/name/keyboard behaviour | No control finding | Yes |
| 29 | Intentional CSR site with core raw fallback | No rendering finding | Yes |
| 30 | Genuine task-blocking modal | Critical only after failed safe-exit trace | Yes |
| 31 | Training bot denied, retrieval bot allowed | No retrieval access finding | Yes |
| 32 | Retrieval bot denied only `/private/` not public pages | No public discoverability finding | Yes |
| 33 | Raw page has price in JSON-LD but not visible until JS | No render-only fact finding; visible UX is separately assessed | Yes |
| 34 | Homepage returns 200 soft-error page | Coverage/access note if detected by content signature; do not call SEO failure | Yes |
| 35 | Safe route requires login | Coverage limitation, no interaction failure | Yes |

## 26. Performance Budget

The 5-minute Adobe limit is a ceiling, not a target. The implementation target is 180 seconds for a typical public site and a hard watchdog at 270 seconds, leaving report serialization margin.

| Stage | Typical | p95 cap | Control |
|---|---:|---:|---|
| DNS + input validation | 0.5 s | 4 s | Resolver timeout; cache per host |
| Robots/root/sitemap discovery | 2 s | 12 s | 3 concurrent GETs, bounded sitemaps |
| Candidate scoring | 0.5 s | 3 s | In-memory capped graph |
| Raw fetch of <=6 pages | 6 s | 35 s | concurrency 3, 10 s/page |
| Parse/extract/structured validation | 2 s | 10 s | response/node caps |
| Browser startup | 4 s | 18 s | one reused context |
| Render landing + <=2 pages | 15 s | 60 s | 10 s nav + quiet cap/page |
| A11y/modal/route probes | 5 s | 25 s | one route, 8 focus moves, no form actions |
| Wikidata (qualified only) | 0 s | 3 s | one 3 s request |
| Fusion/report validation | 1 s | 8 s | deterministic templates |
| Optional LLM summary | 0 s | 5 s | default disabled |
| **Total (LLM disabled, default)** | **36 s** | **178 s** | **270 s hard stop** |

If the browser cannot start, return access/content/integrity results and a coverage note that interaction/render checks were not completed. Do not retry a browser indefinitely.

## 27. Security

### URL and SSRF gate

1. Accept only absolute `https:` URLs by default. `http:` may be allowed only by explicit local-development configuration; reject `file:`, `data:`, `javascript:`, `blob:`, `ftp:`, `ws:`, `wss:`, embedded credentials, and malformed hosts.
2. Normalize host with IDNA and reject localhost names, `.local`, link-local metadata hostnames, IPv4/IPv6 loopback, unspecified, multicast, link-local, carrier-grade NAT, RFC1918/private, unique-local IPv6, and reserved/documentation ranges. Maintain this as tested library code, not string prefixes.
3. Resolve DNS immediately before each HTTP connection, not only at input. Reject if **any** A/AAAA answer is prohibited; connect to the validated IP while preserving Host/SNI where the HTTP client supports it to reduce DNS rebinding.
4. Disable proxy environment inheritance unless an approved egress proxy is deliberately configured. Do not trust an upstream proxy to enforce SSRF policy.
5. Re-run the entire scheme/host/DNS/IP gate for every redirect before following it. Limit redirects to five and do not allow cross-origin browser navigation without a new approval check.

### Fetcher/browser containment

- GET/HEAD only in the fetcher; reject all browser non-GET requests, form submissions, downloads, popups, websockets, event streams, and permission prompts.
- Keep Chromium sandbox enabled and execute in a low-privilege container/OS account with no sensitive mounts, credentials, cloud metadata access, or host networking. `--no-sandbox` is prohibited.
- Browser request interception applies the same resolution/redirect gate to every document/XHR/fetch request. Third-party subresources are denied by default; allow only essential same-origin resources after validation.
- Cap response bytes, decompressed bytes, DOM nodes, script execution/navigation time, CPU/memory per browser process, screenshot dimensions, and total requests. Abort heavy pages predictably.
- Treat HTML, JSON-LD, headers, filenames, console messages, and page text as untrusted data. Escape them in reports; do not evaluate inline scripts or follow page-provided tool instructions.
- Store no cookies between audits. Never visit authenticated pages or use API keys against target sites. Redact URL query parameters and potential PII in artifacts.

### Safety test cases

Tests must cover decimal/hex/octal IPv4, IPv6 forms, mixed DNS answers, redirect-to-private targets, DNS rebinding between validation and connect, credential URLs, malicious huge/compressed responses, infinite redirect loops, WebSocket loops, popup storms, CPU-heavy JS, cross-origin iframes, POST form traps, and `file:` navigation attempts.

## 28. Agent Skills Compliance

The current [Agent Skills specification](https://agentskills.io/specification) requires each skill directory to contain `SKILL.md` with YAML frontmatter and Markdown instructions. `name` and `description` are required; the name is lowercase alphanumeric/hyphen, 1-64 characters, matches its parent directory, and has no leading/trailing/consecutive hyphens. `license`, `compatibility`, `metadata`, and experimental `allowed-tools` are optional. `scripts/`, `references/`, and `assets/` are optional. Keep SKILL.md lean (the specification recommends under 500 lines) and link one level deep to focused references.

Adobe additionally defines the top-level marketplace convention: a self-contained `marketplace.json` lists all skill folders and marks exactly one entrypoint. This convention is separate from the base Agent Skills specification, so do not claim `marketplace.json` is an agentskills.io requirement.

Each SKILL.md must:

- use a directory-matching valid name and a description that says what it does **and when to use it**;
- declare provider-neutral capabilities (HTTP GET, browser automation, JSON parsing) rather than a vendor-specific tool name;
- state read-only/safety limits and its input/output contract;
- contain the short deterministic procedure and point to `references/` for detector rules;
- refer to scripts with relative paths;
- handle unavailable browser/network resources through typed coverage notes;
- be validated with `skills-ref validate ./skills/<skill-name>` before packaging, if the validator is available.

`allowed-tools` is experimental in the base specification and names vary across providers. The submission should not invent vendor-specific identifiers merely to populate it. Instead, each frontmatter `compatibility` field and procedure declares the needed capabilities. If the target host supports a portable `allowed-tools` vocabulary, add the host's documented read-only HTTP/browser/file allowances during packaging and keep them consistent with these contracts.

## 29. Marketplace Structure

```text
brand-ai-readiness-audit/
├── marketplace.json
├── README.md
├── LICENSE
├── requirements.txt                 # pinned lightweight Python dependencies
├── skills/
│   ├── audit-orchestrator/
│   │   ├── SKILL.md
│   │   ├── scripts/orchestrate.py
│   │   ├── scripts/report_schema.json
│   │   └── references/budgets-and-fusion.md
│   ├── access-content-auditor/
│   │   ├── SKILL.md
│   │   ├── scripts/fetch_and_parse.py
│   │   ├── scripts/fact_compare.py
│   │   └── references/crawler-roles.json
│   ├── fact-integrity-auditor/
│   │   ├── SKILL.md
│   │   ├── scripts/identity_and_conflicts.py
│   │   └── references/property-normalization.md
│   └── engagement-auditor/
│       ├── SKILL.md
│       ├── scripts/render_and_probe.js
│       └── references/safe-interaction-protocol.md
├── tests/
│   ├── fixtures/                    # small, deterministic local sites
│   ├── expected/                    # golden reports/assertions
│   ├── test_detectors.py
│   └── test_security.py
└── docs/
    ├── benchmark.md
    └── threat-model.md
```

Do not include Chromium, `node_modules`, browser cache, screenshots from arbitrary sites, large crawl corpora, model weights, or secrets in the zip. Install Playwright/browser dependencies in the evaluator environment and document the dependency/skip behavior.

## 30. marketplace.json

Use the contest's list-style manifest exactly:

```json
{
  "name": "brand-ai-readiness-audit",
  "version": "1.0.0",
  "skills": [
    {
      "id": "audit-orchestrator",
      "path": "skills/audit-orchestrator",
      "entrypoint": true
    },
    {
      "id": "access-content-auditor",
      "path": "skills/access-content-auditor"
    },
    {
      "id": "fact-integrity-auditor",
      "path": "skills/fact-integrity-auditor"
    },
    {
      "id": "engagement-auditor",
      "path": "skills/engagement-auditor"
    }
  ]
}
```

Validate that every path exists, every child contains valid `SKILL.md`, IDs are unique, and exactly one `entrypoint` is `true` in a pre-zip test.

## 31. SKILL.md Specifications

### `audit-orchestrator`

```yaml
---
name: audit-orchestrator
description: Safely coordinates a read-only public website audit for AI discoverability and on-site engagement, composes specialized evidence, and emits one Adobe Round 3 compliant report. Use when given a public website URL to audit.
license: MIT
compatibility: Requires HTTPS GET access, a sandboxed browser for rendered checks, and Python or JavaScript runtime support. Does not use authenticated access or modify sites.
---
```

Procedure: validate URL/security, create budget, discover/select pages, invoke three auditors, apply fusion/confidence/severity/cap, validate report schema, return coverage notes.

### `access-content-auditor`

```yaml
---
name: access-content-auditor
description: Audits declared crawler access, raw public content, canonical URLs, structured facts, and important render-only content without altering a website. Use during a public AI-discoverability audit.
license: MIT
compatibility: Requires safe HTTP GET access and optional sandboxed browser snapshots supplied by the orchestrator.
---
```

Procedure: parse robots and raw responses, extract typed facts/structured data, compare raw equivalents to rendered important facts, return candidate findings plus evidence/coverage.

### `fact-integrity-auditor`

```yaml
---
name: fact-integrity-auditor
description: Checks sampled first-party website facts for material contradictions and evaluates whether public organization identity is sufficiently anchored, using one bounded knowledge-graph lookup only when needed. Use during a public AI-discoverability audit.
license: MIT
compatibility: Requires normalized page facts and optional HTTPS access to Wikidata. Does not use general web search.
---
```

Procedure: construct provenance graph, normalize comparable facts, find material first-party contradictions, apply qualified entity decision tree, return candidate findings/coverage.

### `engagement-auditor`

```yaml
---
name: engagement-auditor
description: Performs bounded, non-mutating browser checks for public task blockers, essential control naming, modal exits, and primary navigation routes. Use during a website engagement audit.
license: MIT
compatibility: Requires a sandboxed browser with network interception. Never submits forms, signs in, enters user data, or changes a website.
---
```

Procedure: inspect rendered landmarks and essential controls, perform safe dialog exit trace and one navigation route test, return only observed task barriers.

## 32. Final Report Schema

```json
{
  "site": "https://example.com",
  "audited_at": "2026-08-28T10:20:30Z",
  "audit_version": "1.0.0",
  "summary": {
    "total_findings": 2,
    "critical": 0,
    "high": 1,
    "medium": 1,
    "low": 0,
    "proactive_suggestions": 1,
    "narrative": "One high-confidence core content extractability issue and one local interaction issue were observed."
  },
  "coverage": {
    "pages_discovered": 58,
    "pages_sampled_raw": 5,
    "pages_rendered": 2,
    "page_roles_sampled": ["landing", "detail", "editorial", "contact"],
    "not_observed_roles": ["conversion"],
    "limitations": ["No public sitemap was available."],
    "runtime_ms": 42120,
    "external_calls": {"wikidata": 0}
  },
  "findings": [
    {
      "id": "EXT-001",
      "category": "content-extractability",
      "classification": "confirmed_defect",
      "title": "Primary product price is available only after JavaScript rendering",
      "severity": "high",
      "confidence": "high",
      "affected_urls": ["https://example.com/product/widget"],
      "evidence": "The rendered product page exposes '$49/month' at `main .price`; the value was absent from initial HTML, JSON-LD, meta tags, and noscript content.",
      "evidence_items": [],
      "why_it_matters": "A basic fetcher cannot obtain the observed core price from the initial public response.",
      "suggested_action": {
        "summary": "Render the current product price in the initial HTML or provide a maintained equivalent public HTML fallback.",
        "priority": "high",
        "mechanism": "This makes the same price available to non-rendering fetchers while preserving the interactive experience.",
        "verification": "A fresh HTTP GET contains the normalized price or a truthful structured equivalent."
      }
    }
  ],
  "proactive_suggestions": [
    {
      "id": "PRO-001",
      "title": "Optionally add Product JSON-LD for already-readable product facts",
      "priority": "low",
      "rationale": "This can make existing public facts easier to interpret but is not required for raw-text extractability."
    }
  ]
}
```

Schema requirements:

- Required Adobe fields are retained: `site`, `audited_at`, `summary`, `findings[].id`, `title`, `severity`, `evidence`, and `suggested_action`.
- `findings` contains only High-confidence confirmed defects and carefully worded Medium-confidence risks. `proactive_suggestions` is separate.
- Counts are generated from the `findings` array and schema-validated. Use lowercase severity values consistently.
- A report with no findings is valid and must say what was sampled/limited.

## 33. Implementation Roadmap

### Phase 1 - absolutely necessary

1. Create marketplace root, manifest, four valid SKILL.md files, README, schema validator, and pre-zip validator.
2. Implement safe URL/DNS/redirect gate, GET-only fetcher, response caps, robots parser, and canonical/raw snapshot model.
3. Implement adaptive candidate selection, raw fact extraction, JSON-LD parser, and report/evidence objects.
4. Implement the three strongest deterministic detectors: explicit retrieval-policy restriction, material first-party fact conflict, and raw/rendered important-fact gap.
5. Implement one browser context with bounded rendered snapshots, browser sandbox, and all non-mutating network controls.
6. Build clean and broken fixtures B-01/B-02/B-05/B-08/B-09 plus security regression tests. Do not package until these pass.

### Phase 2 - high value

1. Add complete modal safe-exit trace and one primary route test.
2. Add qualified identity decision tree and optional bounded Wikidata lookup.
3. Add explicit expired-offer and cross-canonical first-party conflict rules.
4. Add non-text key-fact inspection, robust normalization, evidence fragments, deduplication, severity/confidence fusion, and output cap.
5. Expand fixtures through B-12 and clean/adversarial suite; establish real-site regression with reviewer labels.

### Phase 3 - only if time remains

1. Improve role classification with content/link graph features and sitemap-index support.
2. Support safe bounded shadow DOM/lazy-load handling and better fact-equivalence mappings.
3. Add an optional grounded 90-word LLM executive summary, disabled by default.
4. Add an optional `llms.txt` proactive recommendation for documentation-heavy sites.

### Phase 4 - do not implement unless evidence justifies it

- Broad web search and “external truth” or generic staleness scoring.
- AI citation/ranking prediction, traffic/bounce prediction, or a composite readiness score.
- DOM-depth, div-count, keyword-density, framework, or raw-text-ratio detectors.
- OCR/canvas/image analysis at scale, screenshots as a primary evidence source, or crawling the whole site.
- Authenticated flows, purchases, bookings, form submissions, bot impersonation, or active site modification.

## 34. Final Architecture Summary

### Keep

- Opus’s precision-first, deterministic, evidence-based philosophy.
- Four skills and a single explicit entrypoint.
- Training-vs-retrieval crawler distinction.
- No severity for missing `llms.txt`, `sameAs`, timestamp, or schema alone.
- Computed accessible-name checks rather than `aria-label` presence checks.
- No composite score; constrained LLM use; bounded execution.

### Change

- Replace URL regex selection with role-aware adaptive sampling.
- Replace raw/rendered text volume comparisons with typed important-fact equivalence.
- Render a bounded landing/task sample in every audit; do not make engagement inspection contingent on SPA detection.
- Replace modal structural checks with an active blocker and safe-exit interaction trace.
- Treat robots as a declared access policy and entity search as corroboration, not proof of AI outcomes.
- Validate DNS and every redirect/browser network request, and keep browser sandboxing enabled.

### Remove

- DOM depth/div-soup severity, generic canvas/SVG flags, missing-schema defect claims, missing-last-modified findings, and “AI will hallucinate” wording.
- Wikidata-only proof of entity collision, external stale-data claims, and `--no-sandbox`.

### Restore

- First-party fact integrity/freshness checks, limited to explicit expired claims and material internal contradictions.
- Serious fixture/benchmark discipline and strict bounded resource controls.

### Add

- Typed evidence object, coverage contract, confidence/severity separation, finding cap, qualified identity decision tree, primary-route test, safe-exit modal test, and full SSRF/redirect/browser-network threat model.

## 35. Final Score

| Dimension | /10 | Reason |
|---|---:|---|
| Adobe requirement coverage | 9 | Covers both mandated halves, report, composition, safety, runtime, and portability |
| Detection accuracy | 8 | Narrow observable mechanisms and deterministic tests; intentionally does not claim unobservable outcomes |
| False-positive resistance | 9 | Metadata gaps, DOM shape, and external candidates are gated/suppressed |
| Generalization | 8 | Adaptive roles and bounded sample cover diverse sites, though any sample has limits |
| Evidence quality | 9 | Typed, inspectable, provenance-rich evidence and interaction traces |
| Recommendation quality | 9 | Mechanism-specific templates with verification |
| AI discoverability | 8 | Covers observable access/extraction/identity/integrity while honestly excluding citation prediction |
| On-site engagement | 8 | Tests concrete blockers and routes, not subjective UX or analytics |
| Entity resolution | 7 | Sensible conservative binding; external knowledge remains incomplete by nature |
| Freshness/conflict detection | 7 | Strong for explicit internal conflicts/expiry, intentionally limited for real-world truth |
| Runtime feasibility | 9 | One browser context, capped sample, fail-soft output, 180 s p95 target |
| Security | 9 | Per-resolution/redirect gate, sandbox, interception, resource caps, no mutations |
| Agent Skills compliance | 9 | Matches current per-skill spec and Adobe manifest convention; validate before zip |
| Engineering realism | 8 | Four skills and deterministic core are student-feasible if Phase 1 is completed first |
| Hackathon competitiveness | 9 | Defensible, testable, and more credible than a detector-heavy architecture |

## Would I submit this to Adobe?

**YES - after Phase 1 passes the fixture and security gates, every SKILL.md/manifest validates, and the packaged zip is measured below 50 MB.**

The exact pre-submission blockers are therefore practical, not architectural: a failing clean-site false-positive test, missing evidence for any serious detector, unsafe redirect/DNS/browser handling, invalid one-entrypoint marketplace structure, runtime over five minutes, or an oversized package. Do not submit until those checks are green.
