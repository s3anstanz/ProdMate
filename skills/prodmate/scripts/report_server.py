#!/usr/bin/env python3
"""Serve ProdMate's guided report on this machine only, so the open page updates itself.

Usage: python3 scripts/report_server.py serve <repo> [--port N] [--idle-minutes 120]

Prints one JSON line, {"url": ..., "pid": ...}, then serves <repo>/.prodmate/report.html
on 127.0.0.1 until it has had no requests for --idle-minutes. The page polls
/__prodmate/version and reloads when ProdMate rewrites the report.
"""
import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION_PATH = "/__prodmate/version"


def make_server(report_html, port=0):
    """A server bound to 127.0.0.1 that serves only report_html and its version."""
    report_html = Path(report_html)

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.server.last_request = time.monotonic()
            path = self.path.split("?", 1)[0]
            port = self.server.server_address[1]
            # Only answer requests addressed to this machine, so another website can't
            # point its own domain at 127.0.0.1 (DNS rebinding) and read the report.
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                self.send(404, b"Not found", "text/plain; charset=utf-8")
                return
            try:
                if path == "/":
                    self.send(200, report_html.read_bytes(), "text/html; charset=utf-8")
                elif path == VERSION_PATH:
                    st = report_html.stat()
                    body = json.dumps({"version": f"{st.st_mtime_ns}-{st.st_size}"}).encode()
                    self.send(200, body, "application/json")
                else:
                    self.send(404, b"Not found", "text/plain; charset=utf-8")
            except FileNotFoundError:
                self.send(404, b"The report isn't there yet.", "text/plain; charset=utf-8")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.last_request = time.monotonic()
    return server


def main(argv):
    parser = argparse.ArgumentParser(prog="report_server.py")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("repo")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--idle-minutes", type=float, default=120)
    args = parser.parse_args(argv[1:])

    page = Path(args.repo).resolve() / ".prodmate" / "report.html"
    try:
        server = make_server(page, args.port)
    except OSError as exc:
        print(json.dumps({"error": f"couldn't start the report server: {exc.strerror or exc}"}))
        return 1
    host, port = server.server_address[:2]
    print(json.dumps({"url": f"http://{host}:{port}/", "pid": os.getpid()}), flush=True)

    idle = args.idle_minutes * 60

    def watch():
        while time.monotonic() - server.last_request < idle:
            time.sleep(min(30, idle))
        server.shutdown()

    threading.Thread(target=watch, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
