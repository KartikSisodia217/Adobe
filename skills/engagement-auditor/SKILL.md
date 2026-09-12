---
name: engagement-auditor
description: Performs bounded, non-mutating browser checks for public task blockers, essential control naming, modal exits, and primary navigation routes. Use during a website engagement audit.
license: MIT
compatibility: Requires a sandboxed browser with network interception. Never submits forms, signs in, enters user data, or changes a website.
---
# Engagement Auditor

## When to use
Use during a website engagement audit to check for interaction blockers like trapping modals and inaccessible controls.

## Detection Rules & Reasoning

### G-02: Task-Blocking Modal Trap
*   **Detection Conditions:** Can the user or agent reach the essential task despite a modal being present?
*   **Evidence Requirements:** Must prove that pointer interaction is intercepted (e.g. `document.body.inert`, `overflow: hidden`, or `<dialog open>`) AND that safe exit attempts (Escape key, clicking close buttons) fail. Must trace focus to prove focus is trapped.
*   **False-Positive Exclusions:** A modal existing (`role="dialog"`) does not automatically mean the route is blocked. If the modal can be bypassed, scrolled past, or safely dismissed, do NOT flag it as a trap.
*   **Severity Criteria:** Critical (a true modal trap prevents all subsequent actions).

### G-03: Primary Route Unreachable
*   **Detection Conditions:** Activating primary navigation links fails to reach a healthy destination.
*   **Evidence Requirements:** Must record original URL, perform click, and evaluate new URL transition OR meaningful content transition. Must verify destination health.
*   **False-Positive Exclusions:** Do not flag merely if Playwright throws an exception. Modern SPAs might not change the URL; ensure destination health is evaluated semantically (e.g. checking for `<main>` content and ensuring no "404 Not Found" exists).
*   **Severity Criteria:** High (impacts core navigation workflow).

### G-01: Unnamed Essential Control
*   **Detection Conditions:** Essential interactive controls (buttons, links, menuitems) lack accessible names.
*   **Severity Criteria:** Low (accessibility flaw but often bypassable by vision models).

### Action Selection & Remediation
*   For G-02: Ensure all modal overlays can be closed safely using the 'Escape' key or standard button clicks without trapping focus.
*   For G-03: Ensure semantic anchor links correctly route to healthy, populated application states.
