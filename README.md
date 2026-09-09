# AIMLESS - Brand AI-Readiness Audit
Marketplace for the Adobe University Hackathon 2026.
Entrypoint: `audit-orchestrator`

## Member 3 prototype

Member 3 provides deterministic first-party fact checks (expired claims, contradictions, and ambiguous identities) and bounded engagement checks. Wikidata is used only for a generic, contradictory identity with no sameAs signal; it has one request, a three-second timeout, evaluates at most five candidates, and can yield only a medium-risk signal.

Engagement checks operate exclusively through `BrowserAdapter`: G-01 detects unnamed essential controls, G-02 uses Escape, an explicit accessible exit, and at most eight focus steps, and G-03 tests one inferred primary navigation link. No forms or mutations are performed.

Run the independently testable fixture demonstration with:

```powershell
python scripts/run_member3_prototype.py
```

Run its tests with:

```powershell
python -m pytest tests/unit/test_member3.py
```
