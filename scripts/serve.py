"""
serve.py — start a local HTTP server and open the graph explorer in your browser.

Usage:
    python scripts/serve.py [--port 8765]
"""
import http.server
import threading
import webbrowser
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()

    import os
    os.chdir(ROOT)

    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(("localhost", args.port), handler)

    url = f"http://localhost:{args.port}/explorer.html"
    print(f"Serving at {url}")
    print("Press Ctrl-C to stop.\n")

    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
