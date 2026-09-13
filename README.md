# AIMLESS: AI-Readiness & Engagement Auditor

The marketplace audits whether a brand is discoverable, understandable, trustworthy, and correctly represented across both its website and the wider web. It is read-only and recommend-only: it never signs in, submits a form, makes a purchase, or changes a live site.

## Cross-Web Brand Discovery & Conflicting Presence Audit

The `brand-identity-audit` skill evaluates whether users and AI systems can discover and verify the official brand/source, distinguish it from stale or conflicting representations across the web, and reach the authoritative destination.

Rather than relying solely on caller-provided sources, the engine performs **bounded, read-only cross-web discovery** (combining first-party outbound platform links, subdomain checks, and bounded public search queries). Discovered representations are categorized using an **evidence-backed classification taxonomy**:
- `first-party`: Verified official domain, canonical host, or verified official social profiles (`sameAs`).
- `historical first-party`: Predecessor domain or hosted platform that shares verified brand identity anchors (same creator, matching brand name, shared social handles) but lacks redirection or explicit official delegation.
- `reseller`: Authorized partner or distributor offering products/services with explicit reseller affiliation.
- `marketplace`: Multi-brand directory or storefront (e.g., Udemy, Amazon, Coursera).
- `third-party`: External site reviewing, discussing, or referencing the brand.
- `unknown`: External source with insufficient evidence for high-confidence classification.

Example findings:
- **Critical — Conflicting authoritative destination (B-01):** An observed historical platform or directory routes transactions or signups to a non-authoritative checkout host.
- **High — Potentially stale or conflicting fact (B-02):** A public listing and official site publish different prices or availability for the same product/service.
- **Medium — Same-name entity ambiguity (B-03):** Another domain presents the same brand name without authoritative identity anchors.
- **Medium — Official-source clarity gap (B-04):** The official site lacks explicit authoritative statements while conflicting representations exist.
- **High — Outdated platform representation (B-05):** A historical platform continues serving users without migration notices or 301 redirects to the authoritative domain.

### Scoring Separation
The audit strictly decouples identity metrics:
- **First-party Identity Confidence:** Measures how clearly the authoritative site declares and structures its own identity.
- **Cross-web Identity Confidence:** Evaluates cross-web consistency. High only when external representations have been evaluated and verified consistent. Defaults to 50 if unassessed.
- **Source Consistency:** Deducts for conflicting destinations, stale prices, or unmigrated platforms.
- **External Conflict Risk:** Escalates proportionally to detected cross-source conflicts.

An **multi-skill agent audit system** designed to evaluate any website's **"AI Discoverability"** and **"On-Site Engagement"**. Built for the Adobe Hackathon Round 3, this tool helps brands understand why they are invisible to AI assistants (like ChatGPT, Claude, or Perplexity) and why visitors or automated agents bounce when they arrive on site.

## Key Features
*   **Security-First Execution:** Bounded network interception, SSRF guards, and strictly non-mutating Playwright interactions.
*   **Heuristic & Structured Fact Extractor:** Extracts and normalizes contextual entities (prices, currencies, billing periods) to find schema contradictions.
*   **Interaction Verification:** Actively traces focus states and evaluates navigation health to prove modal traps and broken routes.
*   **Modular Architecture:** Composed of four discrete, portable skills evaluating discoverability, content access, fact integrity, and engagement safely without violating safety guardrails (SSRF protection, 180s hard timeout limits).

---

## 🏛 Architecture

The project operates as an **Agent Skill Marketplace**, orchestrated by a central Fusion Engine. We enforce strict separation of concerns, executing audits concurrently without violating safety guardrails (SSRF protection, 180s hard timeout limits).

```mermaid
graph TD
    User(["User Payload Input"]) --> CLI["Orchestrator CLI"]
    
    subgraph M1 ["Orchestrator (M1)"]
        CLI --> SecurityGuard["SSRF / DNS Guard"]
        SecurityGuard --> BrowserHost["Playwright Browser Host"]
        SecurityGuard --> Fetcher["Raw HTML Fetcher"]
        SecurityGuard --> Discovery["URL Discovery & Sampling"]
    end

    subgraph M2 ["Access Content (M2)"]
        Fetcher --> Robots["Robots.txt Evaluator"]
        Fetcher --> Extractor["JSON-LD & Fact Extractor"]
    end

    subgraph M3 ["Engagement & Integrity (M3)"]
        BrowserHost --> A11yTree["Accessibility Tree Walker"]
        BrowserHost --> FocusTrap["Modal Trap Tester"]
        Extractor --> FactCheck["Fact Integrity & Contradiction Engine"]
    end

    M2 --> Fusion["Fusion Engine"]
    M3 --> Fusion
    Identity["Brand Identity Audit"] --> Fusion

    subgraph FusionEngine ["Fusion & Reporting"]
        Fusion --> Dedupe["Deduplication"]
        Dedupe --> Cap["Capping & Scoring"]
        Cap --> Report["JSON Report Generator"]
    end

    Report --> FinalJSON(["Adobe Compliant JSON Output"])
```

---

## 📁 Folder Structure

```text
Adobe/
├── .github/workflows/       # CI/CD pipeline (Continuous Integration)
├── docs/                    # Field research trails and architecture references
│   └── field_research.md    # Real-world site studies (Tesla, Amazon, GDPR sites)
├── skills/                  # Core entrypoint execution scripts
│   └── audit-orchestrator/
│       └── scripts/
│           └── orchestrate.py  # Main CLI entrypoint
├── src/
│   ├── access_content/      # M2: Robots checking, Schema.org parsing, Fuzzy semantic extraction
│   ├── browser/             # Playwright network interceptors and stealth evasions
│   ├── engagement/          # M3: Modal/accessibility testing, Interactive flow auditing
│   ├── fact_integrity/      # M3: Date/Price mismatching, Wikidata disambiguation
│   ├── fetching/            # HTTP connection management and raw payload fetches
│   ├── fusion/              # Signal aggregation, severity scoring, and capping
│   ├── orchestration/       # Bootstrapping, Context building, and logger mechanisms
│   ├── reporting/           # Generates final Adobe-compliant JSON reports and narrative summaries
│   ├── robots/              # Robots.txt retrieving
│   ├── sampling/            # Page discovery and BFS crawling (limited depth)
│   ├── schemas/             # Pydantic v1 strictly-typed models
│   └── security/            # Protections against SSRF and arbitrary redirect logic
├── tests/
│   ├── fixtures/            # Mock HTML files and wild-site tests
│   ├── integration/         # Integration tests ensuring end-to-end functionality
│   ├── security/            # Tests enforcing SSRF/DNS safety bounds
│   └── unit/                # Component-level testing
├── requirements.txt         # Production dependencies
└── README.md                # You are here
```

---

## 🚀 Setup & Commands

### Prerequisites
Ensure you have Python 3.10+ installed on your system.

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/KartikSisodia217/Adobe.git
cd Adobe

# Install Python dependencies (including CI-compatible stealth)
pip install -r requirements.txt

# Install Playwright and Linux OS dependencies for Chromium
playwright install --with-deps chromium
```

### 2. Running an Audit
The system is designed to be invoked via a single JSON object passed via standard input (`stdin`). This guarantees stateless container execution.

```bash
# Linux / macOS
export PYTHONPATH="."
echo '{"input_url": "https://example.com"}' | python skills/audit-orchestrator/scripts/orchestrate.py

# Windows (PowerShell)
$env:PYTHONPATH="."
echo '{"input_url": "https://example.com"}' | python skills/audit-orchestrator/scripts/orchestrate.py
```

### 3. Running the Test Suite
The project is covered by unit, integration, and security tests.
```bash
PYTHONPATH="." python -m pytest tests/
```

---

## 🔍 Modules & Core Capabilities

1. **Hardened Browser Configuration**
   * Uses a hardened browser configuration for compatibility with modern client-rendered sites.
   * Modifies viewport and interaction behaviors to simulate realistic modern environments.
2. **Generative Remediation Narratives**
   * Deterministically generates executive summaries ("Narratives") without relying on external LLM APIs (Strict hackathon compliance).
   * Dynamically embeds literal visual code snippets (e.g., `<script type="application/ld+json">`) directly into the Adobe-compliant JSON output to aid developers in fixing errors.
3. **Pure-Python Semantic Extractor**
   * Instead of brittle Regex, relies on standard `difflib` token-set heuristics to semantically map unstructured DOM facts to structured `JSON-LD` facts (e.g. mapping `"$39,990"` directly to `"39990.00"`).
4. **Active Focus Trap Breaker**
   * Dynamically injects keystrokes (`Escape`) and utilizes visual tree traversal to test if modals, cookie walls, or popups completely disable the accessibility tree for automated systems.
5. **Identity and source consistency**
   * Normalizes official-domain, organization, structured-data, destination and observed public-source claims; reports conflicts only where the evidence supports them.
6. **Deterministic readiness scores**
   * The report includes AI discoverability, content extractability, entity clarity, brand identity confidence, source consistency, on-site orientation, and overall readiness scores. They are transparent summaries of evidence-backed findings, not a substitute for findings.

---

## 📚 Field Research & References

Our heuristic detectors are not theoretically derived; they are mapped directly to live architectural faults observed in the wild. Please see `docs/field_research.md` for specific case studies.

**Core Principles Derived From:**
1. *Google Search Central: SEO for AI & Structured Data Guidelines (2024)*
2. *W3C Web Content Accessibility Guidelines (WCAG) 2.2 - Focus Management*
3. *"The JS Rendering Gap" - How Client-Side Rendering Obfuscates Core Commercial Facts (Modern React/Next.js Architecture Patterns).*
4. *Schema.org Ontology completeness requirements for rich snippets.*

---

## 🛡 Guardrails & Security constraints
* **Non-Destructive:** The auditor explicitly blocks form submission (`POST`/`PUT`) and disables arbitrary file downloading.
* **Bounded Execution:** Strict 180-second timeout budget per run, monitored globally by the Orchestrator.
* **SSRF Protection:** Resolves and rejects private CIDR blocks, localhost traversal, and `file://` local read attacks.
* **Robots and rate safety:** Fetching is bounded, respects robots.txt, uses only public GET access, and does not perform rate-abusive external discovery.

## 📄 License
MIT License. Created for the Adobe Hackathon.
