"""Small, reviewable coding agent demo powered by Nebius Token Factory."""
import difflib
import json
import os
import base64
import io
import zipfile
from pathlib import Path
import re
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import request, error

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "sample"
CASES = {
    "average": {"title": "Fractional averages", "description": "The average function rounds fractional results down. average([1, 2]) should return 1.5."},
    "slug": {"title": "Repeated spaces", "description": "The slug function leaves extra hyphens when a title has repeated spaces. 'Hello   World' should become 'hello-world'."},
}
DEFAULT_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
MODEL = os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL)
if MODEL == "nvidia/nvidia-nemotron-3-nano-30b-a3b":
    MODEL = DEFAULT_MODEL
HOSTED_DEMO = os.environ.get("PATCHWORK_DEMO_MODE", "").lower() in {"1", "true", "yes"}
SESSION = {"key": os.environ.get("NEBIUS_API_KEY", "")}
API_URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"
RATE_LOCK = threading.Lock()
RATE_EVENTS = defaultdict(deque)
RATE_LIMIT = int(os.environ.get("PATCHWORK_REQUESTS_PER_HOUR", "12"))


def model_patch(description, source, tests, filename):
    key = SESSION["key"]
    if not key:
        raise ValueError("Add a Token Factory API key in the local setup panel.")
    prompt = (f"Fix the bug in {filename} described below. Return ONLY the complete "
              f"replacement contents for {filename}, without Markdown fences. "
              "Preserve the language, public interfaces, and existing style. Make the smallest sensible change.\n\n"
              f"Bug: {description}\n\n{filename}:\n{source}\n\n"
              f"test_{filename}:\n{tests}")
    payload = json.dumps({"model": MODEL, "messages": [
        {"role": "system", "content": "You are a careful software bug fixing assistant. Preserve the input programming language."},
        {"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 4096}).encode()
    req = request.Request(API_URL, payload, {
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=60) as response:
            data = json.load(response)
    except error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError("Token Factory rejected this API key. Copy the full secret from its creation dialog and reconnect locally.") from exc
        raise RuntimeError(f"Nebius returned HTTP {exc.code}: {exc.read(500).decode(errors='replace')}") from exc
    content = (data["choices"][0]["message"].get("content") or "").strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:python)?\s*|\s*```$", "", content).strip()
    if not content:
        raise RuntimeError("The model returned no patch. Try the request again.")
    if filename.endswith(".py"):
        compile(content, filename, "exec")
    return content + "\n", data.get("usage", {})


def inspect_zip(raw):
    if len(raw) > 2_000_000:
        raise ValueError("ZIP must be smaller than 2 MB.")
    allowed = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md", ".txt"}
    files = {}
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        for item in archive.infolist():
            path = Path(item.filename)
            if item.is_dir() or path.is_absolute() or ".." in path.parts:
                continue
            if len(files) >= 40 or item.file_size > 300_000:
                continue
            if path.suffix.lower() not in allowed:
                continue
            try:
                content = archive.read(item).decode("utf-8")
            except (UnicodeDecodeError, zipfile.BadZipFile):
                continue
            files[item.filename] = content
    except (zipfile.BadZipFile, OSError):
        raise ValueError("That file is not a readable ZIP archive.")
    if not files:
        raise ValueError("No supported text source files found in the ZIP.")
    return files


def propose(description, filename, source):
    if len(source) > 30_000 or len(description) > 1200:
        raise ValueError("Keep the selected source file under 30 KB and bug report under 1,200 characters.")
    proposed, usage = model_patch(description, source, "User project tests are not run in this local prototype.", filename)
    diff = "".join(difflib.unified_diff(source.splitlines(True), proposed.splitlines(True),
                                         fromfile=f"a/{filename}", tofile=f"b/{filename}"))
    return {"filename": filename, "proposed": proposed, "diff": diff,
            "status": "Patch ready for review � tests not run", "model": MODEL, "usage": usage}


def check_rate_limit(client_ip):
    """Apply a generous per-client cap to protect a publicly hosted demo key."""
    now = time.monotonic()
    cutoff = now - 3600
    with RATE_LOCK:
        events = RATE_EVENTS[client_ip]
        while events and events[0] < cutoff:
            events.popleft()
        if len(events) >= RATE_LIMIT:
            raise ValueError("Demo request limit reached for this hour. Please try again later.")
        events.append(now)


def run_case(source, tests, filename):
    # Arbitrary generated and uploaded code is never executed by this server.
    return {"passed": None, "output": "Not run: isolated container execution is not configured."}


def analyse(description, case):
    if case not in CASES:
        raise ValueError("Unknown exercise.")
    filename = "calculator.py" if case == "average" else "slug.py"
    source = (SAMPLE / filename).read_text(encoding="utf-8")
    tests = (SAMPLE / f"test_{filename}").read_text(encoding="utf-8")
    before = run_case(source, tests, filename)
    proposed, usage = model_patch(description, source, tests, filename)
    after = run_case(proposed, tests, filename)
    diff = "".join(difflib.unified_diff(source.splitlines(True), proposed.splitlines(True),
                                         fromfile=f"a/{filename}", tofile=f"b/{filename}"))
    return {"before": before, "after": after, "diff": diff,
            "status": "Tests not run � isolated execution unavailable",
            "model": MODEL, "usage": usage}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            self.json_response({"configured": bool(SESSION["key"]), "hosted": HOSTED_DEMO, "model": MODEL})
            return
        if self.path.startswith("/sample/"):
            name = Path(self.path.removeprefix("/sample/")).name
            if name not in {"calculator.py", "slug.py", "test_calculator.py", "test_slug.py"}:
                self.send_error(404)
                return
            self.respond((SAMPLE / name).read_bytes(), "text/plain; charset=utf-8")
            return
        if self.path != "/":
            self.send_error(404)
            return
        self.respond((ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")

    def do_POST(self):
        if self.path not in ("/api/analyse", "/api/config", "/api/upload", "/api/propose"):
            self.send_error(404)
            return
        try:
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://{host}", f"https://{host}"):
                raise ValueError("Request must come from this Patchwork site.")
            if not HOSTED_DEMO and host not in ("127.0.0.1:8000", "localhost:8000"):
                raise ValueError("Local mode only accepts requests from this computer.")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Requests must use application/json.")
            length = int(self.headers.get("Content-Length", "0"))
            limit = 2_800_000 if self.path == "/api/upload" else 50_000
            if not 0 < length <= limit:
                raise ValueError("Request is too large.")
            body = json.loads(self.rfile.read(length))
            if self.path == "/api/upload":
                raw = base64.b64decode(body.get("zip", ""), validate=True)
                files = inspect_zip(raw)
                result = {"files": files, "count": len(files)}
            elif self.path == "/api/propose":
                if HOSTED_DEMO:
                    client_ip = (self.headers.get("CF-Connecting-IP")
                                 or self.headers.get("X-Real-IP")
                                 or self.client_address[0])
                    check_rate_limit(client_ip)
                result = propose(str(body.get("description", "")), str(body.get("filename", "project.py")), str(body.get("source", "")))
            elif self.path == "/api/config":
                if HOSTED_DEMO:
                    raise ValueError("The hosted demo uses its server-side Token Factory key.")
                key = str(body.get("key", ""))
                if len(key) < 20 or any(char.isspace() or char in "\"'" for char in key):
                    raise ValueError("Paste only the complete API key copied from Token Factory.")
                SESSION["key"] = key
                result = {"configured": True, "model": MODEL}
            else:
                result = analyse(str(body.get("description", ""))[:1200], str(body.get("case", "average")))
            status = 200
        except Exception as exc:
            result, status = {"error": str(exc)}, 400
        self.json_response(result, status)

    def json_response(self, data, status=200):
        self.respond(json.dumps(data).encode(), "application/json", status)

    def respond(self, body, mime, status=200):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    host = "0.0.0.0" if HOSTED_DEMO else "127.0.0.1"
    print(f"Patchwork: http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()

