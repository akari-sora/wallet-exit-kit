"""Local JSON-RPC stand-in. Binds to 127.0.0.1 only."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n).decode())
            resp = self.server.dispatch(body)
        except Exception as exc:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": type(exc).__name__}}
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        return


class _Server(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def jsonrpc_ok(req, result):
    return {"jsonrpc": "2.0", "id": req.get("id"), "result": result}


def jsonrpc_err(req, message):
    return {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32000, "message": message}}


def serve(dispatch):
    httpd = _Server(("127.0.0.1", 0), _Handler)
    httpd.dispatch = dispatch
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}"
    return httpd, url


def collect_methods(body, into):
    if isinstance(body, list):
        for item in body:
            collect_methods(item, into)
        return
    if isinstance(body, dict) and isinstance(body.get("method"), str):
        into.append(body["method"])


def routed(handlers, seen):
    def one(req):
        fn = handlers.get(req.get("method"))
        if fn is None:
            return jsonrpc_err(req, "unexpected")
        return fn(req)

    def dispatch(body):
        collect_methods(body, seen)
        if isinstance(body, list):
            return [one(item) for item in body]
        return one(body)

    return dispatch
