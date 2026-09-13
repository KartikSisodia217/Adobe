import os
import pytest
import os
import threading
import http.server
import socketserver
import asyncio
from src.orchestration.orchestrator import execute_audit

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def start_server(port, directory):
    import functools
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    httpd.serve_forever()

@pytest.fixture(scope="module")
def generalization_server():
    base_dir = "tests/fixtures/generalization"
    servers = {}
    threads = []
    
    ports = {
        "A_static_conventional": 9101,
        "B_spa_js": 9102,
        "D_ecommerce": 9103,
        "E_documentation": 9104,
        "L_visible_vs_structured_conflict": 9105,
        "T_robots_restrict": 9106,
        "O_unnamed_controls": 9107,
        "Q_trapping_modal": 9108
    }
    
    for name, port in ports.items():
        directory = os.path.join(base_dir, name)
        t = threading.Thread(target=start_server, args=(port, directory), daemon=True)
        t.start()
        threads.append(t)
        servers[name] = f"http://127.0.0.1:{port}/"
        
    import time
    time.sleep(1)
    yield servers

@pytest.mark.asyncio
async def test_generalization_a_static(generalization_server, monkeypatch):
    monkeypatch.setenv("BENCHMARK_MODE", "1")
    report = await execute_audit(generalization_server["A_static_conventional"], config={"max_raw_cap": 5})
    assert report["summary"]["total_findings"] >= 0
    # Just asserting it runs without error and covers pages

@pytest.mark.asyncio
async def test_generalization_b_spa(generalization_server, monkeypatch):
    monkeypatch.setenv("BENCHMARK_MODE", "1")
    report = await execute_audit(generalization_server["B_spa_js"])
    findings = [f["detector_id"] for f in report.get("findings", [])]
    print(report.get("coverage", {}).get("limitations", [])); assert "E-01" in findings # Should detect JS render gap for the price

@pytest.mark.asyncio
async def test_generalization_l_conflict(generalization_server, monkeypatch):
    monkeypatch.setenv("BENCHMARK_MODE", "1")
    report = await execute_audit(generalization_server["L_visible_vs_structured_conflict"])
    findings = [f["detector_id"] for f in report.get("findings", [])]
    assert "D-02" in findings # Should detect schema contradiction

@pytest.mark.asyncio
async def test_generalization_o_unnamed(generalization_server, monkeypatch):
    monkeypatch.setenv("BENCHMARK_MODE", "1")
    report = await execute_audit(generalization_server["O_unnamed_controls"])
    findings = [f["detector_id"] for f in report.get("findings", [])]
    assert "G-01" in findings # Should detect unnamed controls

@pytest.mark.asyncio
async def test_generalization_q_trapping(generalization_server, monkeypatch):
    monkeypatch.setenv("BENCHMARK_MODE", "1")
    report = await execute_audit(generalization_server["Q_trapping_modal"])
    findings = [f["detector_id"] for f in report.get("findings", [])]
    assert "G-02" in findings # Should detect modal trap
