import asyncio
import json
import time
from src.orchestration.orchestrator import execute_audit

# Example Ground Truth for benchmarking
GROUND_TRUTH = {
    "https://example.com": {"expected_findings": 0},
    "https://mock-defective-site.com/": {"expected_findings": 2}
}

async def run_benchmark():
    print("Starting AIMLESS Benchmark Harness...")
    results = []
    
    total_start = time.time()
    for url, truth in GROUND_TRUTH.items():
        print(f"Auditing {url}...")
        try:
            report = await execute_audit(url)
            actual_findings = report.get("summary", {}).get("total_findings", 0)
            
            # Simple eval
            expected = truth["expected_findings"]
            is_correct = (expected == 0 and actual_findings == 0) or (expected > 0 and actual_findings > 0)
            
            results.append({
                "url": url,
                "runtime_ms": report.get("coverage", {}).get("runtime_ms", 0),
                "is_correct": is_correct
            })
        except Exception as e:
            print(f"Error auditing {url}: {e}")
            
    total_time = time.time() - total_start
    
    correct = sum(1 for r in results if r["is_correct"])
    accuracy = correct / len(results) if results else 0
    
    print("\n--- Benchmark Results ---")
    print(f"Total Sites: {len(results)}")
    print(f"Overall Accuracy (Detection Precision): {accuracy*100:.1f}%")
    print(f"Total Runtime: {total_time:.2f}s")
    print("-------------------------\n")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
