# AIMLESS Brand AI-Readiness Auditor

An autonomous, multi-agent auditing system designed to evaluate any website's "AI Discoverability" and "On-Site Engagement". Built for the Adobe Hackathon Round 3, this tool helps brands understand why they are invisible to AI assistants (like ChatGPT or Perplexity) and why visitors bounce when they arrive.

## 🚀 What it does

The AIMLESS auditor runs a non-destructive, read-only analysis of a target website. It generates a standardized JSON report highlighting exactly what needs to be fixed.

It detects critical AI-visibility traps, including:
* **Robots.txt Blocking:** Are you explicitly blocking AI retrieval bots?
* **JS Rendering Gaps:** Are your core product facts (prices, availability) trapped in client-side JavaScript, making them invisible to simple crawlers?
* **Schema Contradictions:** Does your visible text contradict your hidden `JSON-LD` structured data?
* **Accessibility & Modal Traps:** Are there aggressive cookie banners or inaccessible navigation routes that prevent automated agents from completing tasks?
* **Fact Expiration & Ambiguity:** Are your claims outdated, or is your brand identity easily confused with competitors by AIs?

## 🧠 System Architecture

The project is built as an **Agent Skill Marketplace** composed of three highly decoupled modules, orchestrated by a central engine:

1. **Audit Orchestrator (Entrypoint):** Manages the execution lifecycle, Playwright browser host, security gates (SSRF/DNS validation), timeout budgets (180s target), and the final Fusion engine that deduplicates and scores findings.
2. **Access-Content Auditor:** Responsible for HTTP-level retrieval parsing, `JSON-LD` structured data extraction (using robust fuzzy semantic matching), and raw vs. rendered fact comparison.
3. **Fact-Integrity & Engagement Auditor:** Responsible for bounded interaction tests. Uses the accessibility tree to detect focus traps, essential unnamed controls, and performs first-party factual consistency checks (including Wikidata disambiguation).

## 🛠️ Installation

Ensure you have Python 3.10+ installed.

```bash
# Clone the repository
git clone https://github.com/KartikSisodia217/Adobe.git
cd Adobe

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (Required for the Engagement Auditor)
playwright install chromium
```

## 💻 Usage

The system is designed to be invoked via a single JSON object passed via standard input (stdin).

```bash
# Set PYTHONPATH to the project root
export PYTHONPATH="."

# Run the audit against a target URL
echo '{"input_url": "https://example.com"}' | python skills/audit-orchestrator/scripts/orchestrate.py
```

### Example Output
The system outputs a deterministic, Adobe-compliant JSON report containing a severity-scored summary and actionable findings:

```json
{
  "site": "https://example.com/",
  "audited_at": "2026-09-12T06:07:36Z",
  "audit_version": "1.0.0",
  "summary": {
    "total_findings": 1,
    "critical": 0,
    "high": 1,
    "medium": 0,
    "low": 0
  },
  "findings": [
    {
      "id": "F-001",
      "title": "Rendering gap",
      "severity": "high",
      "evidence": "Found 1 issues relating to rendering gap.",
      "suggested_action": {
        "summary": "Address rendering gap on core facts",
        "priority": "high"
      }
    }
  ]
}
```

## 🛡️ Guardrails & Security
* **Non-Destructive:** The auditor will never mutate data, submit forms, or bypass authentication.
* **Bounded Execution:** Hard timeouts (180s target, 270s hard kill) ensure the system never hangs.
* **SSRF Protection:** Explicitly rejects auditing `localhost`, private IP ranges, and `file://` protocols.

## 📄 License
MIT License
