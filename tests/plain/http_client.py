"""The HTTP helper against a real local server: JSON, errors, timeouts, partial downloads.

    python tests/plain/http_client.py
"""
import importlib.util
import json
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ab_http", ROOT / "asset_bridge_fork" / "helpers" / "http.py")
http = importlib.util.module_from_spec(spec)
spec.loader.exec_module(http)

checks = 0


def check(name, condition):
    global checks
    assert condition, name
    checks += 1
    print("PASS:", name)


BODY = bytes(range(256)) * 1000
CSV = "name,size\nalpha,1\nbeta,2\nčšž,3\n"


class Handler(BaseHTTPRequestHandler):
    seen_agents = []

    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self.send_response(404 if self.path == "/missing" else 200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        Handler.seen_agents.append(self.headers.get("User-Agent"))
        path = self.path
        if path == "/json":
            data = json.dumps({"a": [1, 2], "name": "čaj"}).encode()
            return self.reply(200, data, "application/json")
        if path == "/csv":
            return self.reply(200, CSV.encode("utf-8"), "text/csv")
        if path == "/file":
            return self.reply(200, BODY)
        if path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/file")
            self.send_header("Content-Length", "0")
            return self.end_headers()
        if path == "/missing":
            return self.reply(404, b"nope")
        if path == "/busy":
            return self.reply(503, b"later")
        if path == "/slow":
            time.sleep(2)
            return self.reply(200, b"{}")
        if path == "/short":  # promises more than it sends
            self.send_response(200)
            self.send_header("Content-Length", str(len(BODY)))
            self.end_headers()
            self.wfile.write(BODY[:1000])
            self.wfile.flush()
            self.close_connection = True
            return
        self.reply(500, b"?")

    def reply(self, status, body, content_type="application/octet-stream"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"

check("get_json reads and decodes", http.get_json(f"{base}/json") == {"a": [1, 2], "name": "čaj"})
check("sends its own User-Agent", http.USER_AGENT in Handler.seen_agents and "Python-urllib" not in str(Handler.seen_agents))
check("iter_lines decodes utf-8", list(http.iter_lines(f"{base}/csv")) == [line + "\n" for line in CSV.splitlines()])

for path, status in (("/missing", 404), ("/busy", 503)):
    try:
        http.get_json(f"{base}{path}")
        raised = None
    except http.HttpError as error:
        raised = error
    check(f"{path}: HttpError with status {status}", raised is not None and raised.status == status)
    check(f"{path}: HttpError is an OSError", isinstance(raised, OSError))

start = time.time()
try:
    http.get_json(f"{base}/slow", timeout=0.3)
    timed_out = False
except OSError:
    timed_out = True
check("a slow server times out", timed_out and time.time() - start < 1.5)

try:
    http.get_json("http://127.0.0.1:1/", timeout=2)
    refused = False
except OSError:
    refused = True
check("a refused connection is an OSError", refused)

with tempfile.TemporaryDirectory() as folder:
    target = Path(folder) / "sub" / "file.bin"
    result = http.download_to(f"{base}/file", target)
    check("download returns the path", result == target)
    check("download content is exact", target.read_bytes() == BODY)
    check("no .part file left", not list(Path(folder).rglob("*.part")))

    redirected = http.download_to(f"{base}/redirect", Path(folder) / "redirected.bin")
    check("redirects are followed", redirected.read_bytes() == BODY)

    # An interrupted download must not leave the file behind
    broken = Path(folder) / "broken.bin"
    try:
        http.download_to(f"{base}/short", broken)
        failed = False
    except OSError:
        failed = True
    check("a short download raises OSError", failed)
    check("a short download leaves no file", not broken.exists() and not list(Path(folder).glob("broken*")))

    # An existing good file survives a failed re-download
    keep = Path(folder) / "keep.bin"
    keep.write_bytes(b"old")
    try:
        http.download_to(f"{base}/missing", keep)
    except http.HttpError:
        pass
    check("a failed download keeps the previous file", keep.read_bytes() == b"old")

check("is_online: a server that answers", http.is_online(f"{base}/json"))
check("is_online: an error status still counts", http.is_online(f"{base}/missing"))
check("is_online: nothing listening", not http.is_online("http://127.0.0.1:1/", timeout=1))

server.shutdown()
print(f"ALL {checks} CHECKS PASSED")
