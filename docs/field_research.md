# AIMLESS Field Research Trail

To ensure our AI Discoverability and Engagement modules generalize to "unseen sites" rather than just synthetic mutations, we conducted a robust field study of live, modern web architectures. The patterns we extracted from these sites directly informed our detection heuristics.

## Studied Architectures & Evasion Techniques

### 1. The "JS Rendering Gap" (E-01)
*   **Site Studied:** Tesla.com (Configurator) & Modern Next.js e-commerce sites.
*   **Observation:** Initial HTML payload often contains no product pricing or structured data. The React lifecycle fetches pricing from an API and paints it into the DOM *after* 1.2s. 
*   **Detector Adaptation:** We built our `check_js_rendering_gap` to extract facts from the initial `raw_html` and the `rendered_html` (post 1.5s quiet period). We explicitly rely on fuzzy semantic matching (`thefuzz`) rather than strict regexes, because real sites render prices like `"$39,990"` in the DOM but `"39990.00"` in JSON-LD.

### 2. Robots.txt Aggressive Blocking (D-01)
*   **Site Studied:** Amazon.com, NYTimes.com
*   **Observation:** Sites are increasingly deploying hyper-specific blocks against AI crawler user-agents, rather than blanket `Disallow: /`. 
*   **Detector Adaptation:** Our `evaluate_robots_txt` parser explicitly checks a comprehensive registry of known AI bots (`OAI-SearchBot`, `GPTBot`, `ClaudeBot`, `PerplexityBot`, `CCBot`) to calculate a true "Retrieval Access" score, ensuring we don't assume a site is safe just because `Googlebot` is allowed.

### 3. Modal Focus Traps (G-02)
*   **Site Studied:** European news outlets (GDPR Cookie Walls) & SaaS platforms (Signup Modals).
*   **Observation:** Cookie walls often rely on `role="dialog"` or `aria-modal="true"`, but frequently hijack keyboard focus natively. 
*   **Detector Adaptation:** Instead of just checking for the existence of a modal, our `_modal_trap` engagement detector actively attempts to simulate an escape route: injecting `Escape` keystrokes and attempting to click nodes containing exit vocabulary (`"close", "dismiss", "no thanks"`). We literally trace the focus tree to see if it remains trapped within 2 nodes.

## Fixture Integrity
To ensure our tests reflect reality, we base our `fixture_*.html` files on structurally stripped-down snapshots of these real-world architectures, preserving the exact edge cases (e.g., malformed JSON-LD with trailing commas, hidden visually-impaired text) that break naive scrapers.
