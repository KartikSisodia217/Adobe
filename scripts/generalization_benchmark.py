import asyncio
import time
import sys
import os
import json
import threading
import http.server
import socketserver

os.environ["BENCHMARK_MODE"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.orchestration.orchestrator import execute_audit

def start_server(port, directory):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
        def log_message(self, format, *args):
            pass # silent
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    httpd.serve_forever()

HOLDOUTS = {
    8101: ("d01_unusual_robots", ["D-01"]),
    8102: ("d02_same_entity", ["D-02"]),
    8103: ("d02_diff_products", []),
    8104: ("d02_monthly_annual", []),
    8105: ("d02_variants", []),
    8106: ("e01_render_only", ["E-01"]),
    8107: ("e01_hydrated_present", []),
    8108: ("e02_factual_non_text", ["E-02"]),
    8109: ("e02_decorative", []),
    8110: ("g02_true_modal", ["G-02"]),
    8111: ("g02_non_blocking", []),
    8112: ("g02_focus_trap", ["G-02"]),
    8113: ("g03_trad_nav", []),
    8114: ("g03_spa_nav", []),
    8115: ("g03_nav_404", ["G-03"]),
    8116: ("f03_ambiguous", ["F-03"]),
    8117: ("f03_clear", []),
    8118: ("stale_claim", ["F-01"]),
    8119: ("clean_site", []),
    8120: ("deep_architecture", []),
    8121: ("d01_sneaky_robots", ["D-01"]),
    8122: ("e01_js_price", ["E-01"]),
    8123: ("g03_button_nav", ["G-03"]),
    8124: ("f03_misleading_schema", ["F-03"])
}

async def run_benchmark():
    print("Starting Generalization Benchmark...")
    threads = []
    base_dir = "tests/generalization/holdout"
    for port, (d_name, _) in HOLDOUTS.items():
        directory = os.path.join(base_dir, d_name)
        t = threading.Thread(target=start_server, args=(port, directory), daemon=True)
        t.start()
        threads.append(t)
    
    # Wait for servers to start
    await asyncio.sleep(2)
    
    start_time = time.time()
    
    tp, fp, fn = 0, 0, 0
    detector_stats = {}
    total_sites = len(HOLDOUTS)
    
    architectures = set()
    roles = set()
    templates = set()
    
    for port, (d_name, expected) in HOLDOUTS.items():
        url = f"http://127.0.0.1:{port}/"
        try:
            report = await execute_audit(url)
            found = set([f["detector_id"] for f in report.get("findings", [])])
            expected_set = set(expected)
            
            for d in expected_set:
                if d not in detector_stats:
                    detector_stats[d] = {"tp": 0, "fp": 0, "fn": 0}
            for d in found:
                if d not in detector_stats:
                    detector_stats[d] = {"tp": 0, "fp": 0, "fn": 0}
            
            # Update stats
            for d in expected_set:
                if d in found:
                    tp += 1
                    detector_stats[d]["tp"] += 1
                else:
                    fn += 1
                    detector_stats[d]["fn"] += 1
            for d in found:
                if d not in expected_set:
                    fp += 1
                    detector_stats[d]["fp"] += 1
                    
            coverage = report.get("coverage", {})
            if coverage.get("site_architecture"):
                architectures.add(coverage.get("site_architecture"))
            for r in coverage.get("page_roles_sampled", []):
                roles.add(r)
            for t in coverage.get("templates_sampled", []):
                if t: templates.add(t)
            
        except Exception as e:
            print(f"Error on {url}: {e}")
            fn += len(expected)
            
    runtime = time.time() - start_time
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print("\n--- Holdout Benchmark Results ---")
    print(f"Total Sites: {total_sites}")
    print(f"True Positives: {tp}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"Precision: {precision * 100:.1f}%")
    print(f"Recall: {recall * 100:.1f}%")
    print(f"F1 Score: {f1 * 100:.1f}%")
    print(f"Total Runtime: {runtime:.2f}s")
    
    print("\n[Per-Detector Performance]")
    for d, stats in detector_stats.items():
        dtp = stats["tp"]
        dfp = stats["fp"]
        dfn = stats["fn"]
        dp = dtp / (dtp + dfp) if (dtp + dfp) > 0 else 0
        dr = dtp / (dtp + dfn) if (dtp + dfn) > 0 else 0
        df1 = (2 * dp * dr) / (dp + dr) if (dp + dr) > 0 else 0
        print(f"| {d} | TP: {dtp} | FP: {dfp} | FN: {dfn} | P: {dp:.2f} | R: {dr:.2f} | F1: {df1:.2f} |")
        
    report_data = {
        "development": {
            "precision": None,
            "recall": None,
            "f1": None
        },
        "holdout": {
            "precision": precision,
            "recall": recall,
            "f1": f1
        },
        "site_architecture_coverage": list(architectures),
        "role_coverage": list(roles),
        "template_coverage": list(templates),
        "sample_efficiency": "Not measured",
        "runtime": runtime,
        "limitations": []
    }
    
    with open("generalization_report.json", "w") as f:
        json.dump(report_data, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
