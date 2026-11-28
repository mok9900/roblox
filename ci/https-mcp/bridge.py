"""Read-only Streamable HTTP facade for the official Roblox Studio MCP.
Initial rollout exposes only a CI-local fixture proof. No arbitrary execution.
The HTTP listener is loopback-only; production requires verified Access JWT.
"""
import json
import os
import queue
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROTOCOLS = ("2025-03-26", "2025-06-18", "2025-11-25")
FIXTURE = "ci_only_baseplate_test"
HOST = "127.0.0.1"
PORT = 18765
MAX_BODY = 65536
TOOL = {"name": "verify_ci_studio", "description": "Read-only check of the actual GitHub-hosted local Roblox Studio test fixture. Never edits or publishes a game.", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}}
ALLOWED_ENV = {"SYSTEMROOT","WINDIR","SYSTEMDRIVE","COMSPEC","PATH","PATHEXT","TEMP","TMP","USERPROFILE","LOCALAPPDATA","APPDATA","PROGRAMDATA","PROGRAMFILES","PROGRAMFILES(X86)","HOMEDRIVE","HOMEPATH","GITHUB_ACTIONS","GITHUB_WORKSPACE","RUNNER_OS","USERNAME","NUMBER_OF_PROCESSORS"}
ROOT = Path(__file__).resolve().parents[2]
LOCK = threading.Lock()

def safe_env():
    return {k:v for k,v in os.environ.items() if k.upper() in ALLOWED_ENV}

class Child:
    def __init__(self, argv, cwd=ROOT):
        self.proc = subprocess.Popen(argv, cwd=cwd, env=safe_env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="strict", bufsize=1)
        self.responses = queue.Queue(maxsize=64)
        self.seq = 0
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.proc.stdout:
                if len(line) > 2_000_000:
                    break
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                self.responses.put(value, timeout=1)
        except Exception:
            pass

    def send(self, method, params=None, notification=False):
        self.seq += 1
        request = {"jsonrpc":"2.0","method":method,"params":params or {}}
        if not notification:
            request["id"] = self.seq
        self.proc.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.proc.stdin.flush()
        if notification:
            return None
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            item = self.responses.get(timeout=max(0.01, deadline - time.monotonic()))
            if not isinstance(item, dict) or item.get("id") != self.seq:
                continue
            if "error" in item or "result" not in item:
                raise RuntimeError("upstream MCP request failed")
            return item["result"]
        raise TimeoutError("upstream MCP response timeout")

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill.exe","/PID",str(self.proc.pid),"/T","/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
            else:
                self.proc.kill()
            self.proc.wait(timeout=5)
        finally:
            self.proc.stdout.close()

def local_fixture_count(value):
    """Parse only structured data or MCP text containing JSON, not substring guesses."""
    if isinstance(value, str):
        try:
            return local_fixture_count(json.loads(value))
        except (ValueError, RecursionError):
            return 0
    if isinstance(value, list):
        return sum(local_fixture_count(v) for v in value)
    if isinstance(value, dict):
        name = value.get("name", "")
        file = value.get("file", "")
        exact_name = isinstance(name, str) and name.casefold() in {FIXTURE, FIXTURE+".rbxl", FIXTURE+".rbxlx"}
        exact_file = isinstance(file, str) and file.replace("\\","/").split("/")[-1].casefold() in {FIXTURE+".rbxl", FIXTURE+".rbxlx"}
        if value.get("persistedToCloud") is False and (exact_name or exact_file):
            return 1
        # Structured MCP payloads only; never return raw identities or paths.
        return sum(local_fixture_count(value[k]) for k in ("studios","instances","content","structuredContent","text","result") if k in value)
    return 0

def verify_upstream(argv=None):
    live = argv is None
    def marker(stage):
        # Fixed stage labels only: never log raw tool outputs, paths or tokens.
        if live:
            print("OFFICIAL_STDIO_STAGE=" + stage, flush=True)

    phase = "launcher"
    if live:
        if os.name != "nt" or os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("RUNNER_OS") != "Windows":
            raise RuntimeError("hosted Windows only")
        launcher = Path(os.environ["LOCALAPPDATA"]) / "Roblox" / "mcp.bat"
        if not launcher.is_file() or not (ROOT / "roblox-mcp-stdio.cmd").is_file():
            marker("launcher_missing")
            raise RuntimeError("official launcher missing")
        argv = ["cmd.exe","/d","/c","roblox-mcp-stdio.cmd"]
    if not LOCK.acquire(blocking=False):
        raise RuntimeError("bridge busy")
    child = None
    try:
        phase = "spawn"
        child = Child(argv)
        marker("spawned")
        phase = "initialize"
        init = child.send("initialize", {"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"roblox-ci-readonly-bridge","version":"0.1.1"}})
        if not isinstance(init, dict) or not isinstance(init.get("protocolVersion"), str):
            raise RuntimeError("invalid initialize result")
        child.send("notifications/initialized", notification=True)
        marker("initialized")
        phase = "catalog"
        catalog = child.send("tools/list")
        if not isinstance(catalog,dict) or not isinstance(catalog.get("tools"),list) or not any(t.get("name") == "list_roblox_studios" for t in catalog["tools"] if isinstance(t,dict)):
            raise RuntimeError("official tool missing")
        marker("catalog_verified")
        phase = "list_studios"
        result = child.send("tools/call", {"name":"list_roblox_studios","arguments":{}})
        if not isinstance(result,dict) or result.get("isError"):
            raise RuntimeError("upstream tool failed")
        marker("list_studios_returned")
        phase = "fixture"
        # MCP structuredContent and content can represent the same result.
        # Count only one representation. Never fall back from a conflicting
        # structured result to human-readable text.
        proof = result["structuredContent"] if "structuredContent" in result else result
        count = local_fixture_count(proof)
        marker("fixture_verified" if count == 1 else "fixture_not_verified")
        return {"verified": count == 1, "matching_local_fixtures":count, "source":"official_studio_mcp"}
    except Exception as exc:
        marker(phase + ("_timeout" if isinstance(exc,(queue.Empty, TimeoutError)) else "_failed"))
        raise
    finally:
        try:
            if child:
                child.close()
        finally:
            LOCK.release()

def dispatch(message, verify=verify_upstream):
    if not isinstance(message,dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"),str):
        return {"jsonrpc":"2.0","id":None,"error":{"code":-32600,"message":"Invalid Request"}}
    method, mid = message["method"], message.get("id")
    if "id" not in message:
        return None
    def ok(result):
        return {"jsonrpc":"2.0","id":mid,"result":result}
    def err(code, msg):
        return {"jsonrpc":"2.0","id":mid,"error":{"code":code,"message":msg}}
    params = message.get("params", {})
    if not isinstance(params, dict):
        return err(-32602,"Invalid params")
    if method == "initialize":
        protocol = params.get("protocolVersion")
        return ok({"protocolVersion":protocol if protocol in PROTOCOLS else PROTOCOLS[-1],"capabilities":{"tools":{"listChanged":False}},"serverInfo":{"name":"roblox-ci-readonly","version":"0.1.0"}})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools":[TOOL]})
    if method == "tools/call":
        if params.get("name") != TOOL["name"] or params.get("arguments",{}) != {}:
            return err(-32602,"Unknown tool or invalid arguments")
        try:
            result = verify()
            return ok({"content":[{"type":"text","text":json.dumps(result)}],"isError":not result["verified"]})
        except Exception:
            return ok({"content":[{"type":"text","text":"Official Studio MCP verification unavailable; no successful connection claimed."}],"isError":True})
    return err(-32601,"Method not found")

def build_auth():
    import jwt
    issuer = os.environ["CF_ACCESS_ISSUER"].rstrip("/")
    audience = os.environ["CF_ACCESS_AUD"]
    email = os.environ["CF_ACCESS_ALLOWED_EMAIL"].casefold()
    import re
    if not re.fullmatch(r"https://[a-z0-9-]+\.cloudflareaccess\.com",issuer) or not audience or not email:
        raise RuntimeError("Access issuer/audience/owner required")
    jwks = jwt.PyJWKClient(issuer+"/cdn-cgi/access/certs", timeout=5)
    def authorize(headers):
        token = headers.get("Cf-Access-Jwt-Assertion","")
        if not token or len(token)>16384:
            return False
        try:
            key = jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(token,key.key,algorithms=["RS256"],audience=audience,issuer=issuer,options={"require":["exp","iat","iss","aud","email"]})
            return claims["email"].casefold() == email
        except Exception:
            return False
    return authorize

def make_handler(authorize, verify=verify_upstream, public_origin=""):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def send_body(self, status, data=None):
            payload = b"" if data is None else json.dumps(data,separators=(",",":")).encode()
            self.send_response(status)
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length",str(len(payload)))
            if payload:
                self.send_header("Content-Type","application/json")
            self.end_headers()
            if payload:
                self.wfile.write(payload)
        def guard(self):
            if self.path != "/mcp":
                self.send_body(404)
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in {"https://chatgpt.com", public_origin}:
                self.send_body(403)
                return False
            if not authorize(self.headers):
                self.send_body(401)
                return False
            return True
        def do_POST(self):
            if not self.guard():
                return
            if self.headers.get("Transfer-Encoding") or self.headers.get_content_type() != "application/json":
                self.send_body(415)
                return
            try:
                length = int(self.headers.get("Content-Length","0"))
                if not 0 < length <= MAX_BODY:
                    self.send_body(413)
                    return
                self.connection.settimeout(10)
                raw = self.rfile.read(length)
                response = dispatch(json.loads(raw),verify)
            except (ValueError, OSError, RecursionError):
                self.send_body(400)
                return
            self.send_body(202 if response is None else 200,response)
        def do_GET(self):
            if self.guard():
                self.send_body(405)
        def do_DELETE(self):
            if self.guard():
                self.send_body(405)
    return Handler

if __name__ == "__main__":
    if os.name != "nt" or os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("RUNNER_OS") != "Windows":
        raise SystemExit("GitHub-hosted Windows required")
    origin = os.environ["ROBLOX_MCP_PUBLIC_ORIGIN"]
    server = ThreadingHTTPServer((HOST,PORT),make_handler(build_auth(),public_origin=origin))
    print("ROBLOX_READONLY_HTTP_LOOPBACK_READY",flush=True)
    server.serve_forever()
