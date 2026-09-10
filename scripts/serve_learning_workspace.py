"""Read-only loopback preview. No API, uploads, model calls or workspace writes."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PAGE = Path(__file__).resolve().parents[1] / "apps/learning-workspace/index.html"


def make_server(port: int = 8766) -> ThreadingHTTPServer:
    content = PAGE.read_bytes()  # Fixed bundled asset only; no caller-supplied path.

    class Handler(BaseHTTPRequestHandler):
        def respond(self, code: int, body: bytes, head: bool = False) -> None:
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8" if code == 200 else "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Connection", "close")
            self.end_headers()
            if not head:
                self.wfile.write(body)

        def read_only(self, head: bool = False) -> None:
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if self.headers.get("Host", "") not in allowed:
                self.respond(403, b"Host refused.", head)
                return
            if self.headers.get("Origin") not in (None, *["http://" + host for host in allowed]):
                self.respond(403, b"Origin refused.", head)
                return
            request = urlsplit(self.path)
            if request.scheme or request.netloc or request.path not in ("/", "/index.html") or request.query:
                self.respond(404, b"Not found.", head)
                return
            self.respond(200, content, head)

        def do_GET(self) -> None:
            self.read_only()

        def do_HEAD(self) -> None:
            self.read_only(head=True)

        def do_POST(self) -> None:
            self.respond(405, b"Read-only preview; writes are not available.")

        do_PUT = do_POST
        do_PATCH = do_POST
        do_DELETE = do_POST

        def log_message(self, format: str, *args) -> None:
            return  # Do not record request paths or user-controlled header text.

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f"Preview only: http://127.0.0.1:{server.server_port}/ — Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Preview stopped.")
    finally:
        server.server_close()
