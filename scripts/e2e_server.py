import http.server
import socketserver
import os
import threading

def start_server(port, directory):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
            
    # Allow address reuse
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    print(f"Serving {directory} at port {port}")
    httpd.serve_forever()

fixtures = [
    (8080, "tests/e2e/sites/clean_static"),
    (8081, "tests/e2e/sites/schema_contradiction"),
    (8082, "tests/e2e/sites/js_render_gap"),
    (8083, "tests/e2e/sites/modal_trap"),
    (8084, "tests/e2e/sites/broken_navigation"),
    (8085, "tests/e2e/sites/robots_blocked"),
    (8086, "tests/e2e/sites/ambiguous_entity"),
    (8087, "tests/e2e/sites/expired_offer")
]

if __name__ == "__main__":
    
    threads = []
    for port, d in fixtures:
        t = threading.Thread(target=start_server, args=(port, d), daemon=True)
        t.start()
        threads.append(t)
        
    for t in threads:
        t.join()
