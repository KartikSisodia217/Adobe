---
name: engagement-auditor
description: Performs bounded, non-mutating browser checks for public task blockers, essential control naming, modal exits, and primary navigation routes. Use during a website engagement audit.
license: MIT
compatibility: Requires a sandboxed browser with network interception. Never submits forms, signs in, enters user data, or changes a website.
---
# Engagement Auditor

## When to use
Use during a website engagement audit to check for interaction blockers like trapping modals and inaccessible controls.

## Inputs
`BrowserAdapter` exposing bounded operations.

## Procedure
1. Inspect rendered landmarks and essential controls.
2. Perform safe dialog exit trace (Escape, visible close button, Tab).
3. Perform one navigation route test.
4. Return observed task barriers.

## Output
Candidate findings for G-01, G-02, G-03.
