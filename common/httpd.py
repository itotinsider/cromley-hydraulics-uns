"""Minimal JSON + static-file HTTP server (standard library), shared by every service.

    app = App()
    @app.get("/api/state")
    def state(req): return {...}                       # dict/list → JSON 200
    @app.post("/api/units/<unit>/start")
    def start(req, unit): return 409, {"error": "..."}  # (status, body)
    app.static("/", "web/index.html")
    app.serve(8120)

req.body is the parsed JSON body ({} if none), req.query a dict of single values.
"""

import json
import logging
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

log = logging.getLogger("http")

CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
                 ".json": "application/json", ".csv": "text/csv; charset=utf-8"}


class Request:
    def __init__(self, handler, path, query, body):
        self.handler = handler
        self.path = path
        self.query = query
        self.body = body


class App:
    def __init__(self):
        self.routes = []      # (method, regex, names, fn)
        self.files = {}       # path -> file on disk

    def _add(self, method, pattern, fn):
        names = re.findall(r"<(\w+)>", pattern)
        rx = re.compile("^" + re.sub(r"<\w+>", r"([^/]+)", pattern) + "$")
        self.routes.append((method, rx, names, fn))
        return fn

    def get(self, pattern):
        return lambda fn: self._add("GET", pattern, fn)

    def post(self, pattern):
        return lambda fn: self._add("POST", pattern, fn)

    def static(self, url, path):
        self.files[url] = path

    def route_list(self):
        return [(m, rx.pattern.strip("^$").replace("([^/]+)", "<>")) for m, rx, _, _ in self.routes]

    def serve(self, port, host="0.0.0.0", background=True):
        app = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt, *args):
                pass

            def _send(self, status, body, ctype="application/json"):
                if isinstance(body, (dict, list)):
                    data = json.dumps(body, ensure_ascii=False).encode()
                elif isinstance(body, str):
                    data = body.encode()
                else:
                    data = body
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)

            def _handle(self, method):
                u = urlparse(self.path)
                query = {k: v[-1] for k, v in parse_qs(u.query).items()}
                body = {}
                n = int(self.headers.get("Content-Length") or 0)
                if n:
                    raw = self.rfile.read(n)
                    try:
                        body = json.loads(raw or b"{}")
                    except ValueError:
                        return self._send(400, {"error": "body is not JSON"})
                if method == "GET" and u.path in app.files:
                    p = app.files[u.path]
                    try:
                        with open(p, "rb") as f:
                            data = f.read()
                    except OSError:
                        return self._send(404, {"error": "not found"})
                    return self._send(200, data, CONTENT_TYPES.get(os.path.splitext(p)[1], "application/octet-stream"))
                for m, rx, names, fn in app.routes:
                    if m != method:
                        continue
                    mt = rx.match(u.path)
                    if mt:
                        try:
                            res = fn(Request(self, u.path, query, body), *mt.groups())
                        except Exception as e:  # noqa: BLE001 - report, don't kill the server thread
                            log.exception("%s %s", method, u.path)
                            return self._send(500, {"error": str(e)})
                        # body | (status, body) | (status, body, content-type)
                        if not isinstance(res, tuple):
                            res = (200, res)
                        return self._send(*res)
                return self._send(404, {"error": f"no route {method} {u.path}"})

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Content-Length", "0")
                self.end_headers()

        srv = ThreadingHTTPServer((host, port), Handler)
        srv.daemon_threads = True
        if background:
            threading.Thread(target=srv.serve_forever, daemon=True, name=f"http-{port}").start()
        else:
            srv.serve_forever()
        return srv


def http_json(url, method="GET", body=None, timeout=3.0):
    """Tiny client: returns (status, parsed JSON or None); status None when the server can't be reached."""
    import urllib.error
    import urllib.request
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"error": raw.decode(errors="replace")}
    except (urllib.error.URLError, OSError, ValueError) as e:
        # unreachable, refused, timed out, or not JSON: the caller decides what that means
        return None, {"error": str(e)}
