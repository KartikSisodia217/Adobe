import asyncio
import time
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.orchestration.orchestrator import execute_audit

SITES = [
    "https://example.com",
    "https://httpbin.org/html"
]

async def run_unseen_benchmark():
    print("Starting Unseen Site Benchmark...")
    results = []
    
    for site in SITES:
        print(f"Auditing {site}...")
        start_time = time.time()
        
        try:
            # Enforce 300s total timeout per site at the top level
            report = await asyncio.wait_for(execute_audit(site, discover_external_sources_enabled=False), timeout=300)
            
            coverage = report.get("coverage", {})
            findings = report.get("findings", [])
            runtime = time.time() - start_time
            
            results.append({
                "site": site,
                "status": "success",
                "pages_discovered": coverage.get("pages_discovered", 0),
                "pages_sampled": coverage.get("pages_rendered", 0),
                "roles": coverage.get("page_roles_sampled", []),
                "templates": coverage.get("templates_sampled", []),
                "runtime_seconds": runtime,
                "findings": len(findings),
                "limitations": coverage.get("limitations", [])
            })
            
        except asyncio.TimeoutError:
            print(f"Timeout on {site}")
            results.append({
                "site": site,
                "status": "timeout",
                "pages_discovered": 0,
                "pages_sampled": 0,
                "roles": [],
                "templates": [],
                "runtime_seconds": 300.0,
                "findings": 0,
                "limitations": ["Site timeout"]
            })
        except Exception as e:
            print(f"Error on {site}: {e}")
            runtime = time.time() - start_time
            results.append({
                "site": site,
                "status": "error",
                "pages_discovered": 0,
                "pages_sampled": 0,
                "roles": [],
                "templates": [],
                "runtime_seconds": runtime,
                "findings": 0,
                "limitations": [str(e)]
            })
            
    with open("unseen_site_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n--- Unseen Site Benchmark Results ---")
    for r in results:
        print(f"Site: {r['site']} | Status: {r['status']} | Discovered: {r['pages_discovered']} | Findings: {r['findings']} | Runtime: {r['runtime_seconds']:.2f}s")

if __name__ == "__main__":
    asyncio.run(run_unseen_benchmark())
