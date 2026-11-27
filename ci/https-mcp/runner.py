"""Outbound GitHub-hosted relay. Fixed read-only action; no remote code execution."""
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from bridge import verify_upstream

BASE = "https://roblox-mcp.parcel-mcp-seojun.workers.dev"
AUDIENCE = BASE + "/runner"

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

OPENER = urllib.request.build_opener(NoRedirect())

def read_json(req):
    with OPENER.open(req, timeout=25) as res:
        raw = res.read(65537)
        if len(raw) > 65536:
            raise ValueError("response too large")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("response not an object")
        return value

class Runner:
    def __init__(self):
        self.token = None
        self.refresh = 0

    def get_token(self):
        if self.token and time.monotonic() < self.refresh:
            return self.token
        raw = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
        url = urllib.parse.urlsplit(raw)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment:
            raise RuntimeError("invalid GitHub OIDC request URL")
        if "audience" in dict(urllib.parse.parse_qsl(url.query,keep_blank_values=True)):
            raise RuntimeError("unexpected preconfigured audience")
        target = raw + ("&" if url.query else "?") + "audience=" + urllib.parse.quote(AUDIENCE,safe="")
        try:
            result = read_json(urllib.request.Request(target,headers={"Authorization":"Bearer "+os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],"Accept":"application/json","User-Agent":"roblox-mcp-relay/0.1"}))
        except urllib.error.HTTPError as exc:
            print(f"WORKERS_OIDC_ISSUANCE_HTTP={exc.code}",flush=True)
            raise RuntimeError("OIDC issuance failed") from None
        except Exception:
            print("WORKERS_OIDC_ISSUANCE_TRANSPORT_FAILED",flush=True)
            raise RuntimeError("OIDC issuance failed") from None
        token = result.get("value")
        if not isinstance(token,str) or len(token)>16384 or len(token.split("."))!=3:
            raise RuntimeError("invalid GitHub token")
        self.token = token
        self.refresh = time.monotonic()+60
        return token

    def post(self, path, payload=None):
        if path not in ("/runner/preflight","/runner/poll","/runner/result"):
            raise ValueError("invalid relay path")
        data = json.dumps(payload or {},separators=(",",":")).encode()
        req = urllib.request.Request(BASE+path,data=data,method="POST",headers={"Authorization":"Bearer "+self.get_token(),"Content-Type":"application/json","Accept":"application/json","User-Agent":"roblox-mcp-relay/0.1"})
        try:
            return read_json(req)
        except urllib.error.HTTPError as exc:
            print(f"WORKERS_RELAY_HTTP={exc.code} path={path}",flush=True)
            raise RuntimeError("relay HTTP failed") from None
        except Exception:
            print(f"WORKERS_RELAY_TRANSPORT_FAILED path={path}",flush=True)
            raise RuntimeError("relay transport failed") from None

def execute_job(job, verify=verify_upstream):
    if not isinstance(job,dict):
        raise ValueError("invalid job")
    rid = job.get("request_id")
    if rid is None:
        return None
    if not isinstance(rid,str) or str(uuid.UUID(rid)) != rid or job.get("action") != "verify_ci_studio":
        raise ValueError("invalid job action")
    # Never pass any remote-controlled argument to the official launcher.
    result = verify()
    if not isinstance(result,dict) or type(result.get("verified")) is not bool or type(result.get("matching_local_fixtures")) is not int or result["source"]!="official_studio_mcp":
        raise ValueError("invalid local proof")
    return {"request_id":rid,"result":result}

def hosted_only():
    if os.name!="nt" or os.getenv("GITHUB_ACTIONS")!="true" or os.getenv("RUNNER_OS")!="Windows":
        raise RuntimeError("GitHub-hosted Windows required")

def main():
    hosted_only()
    parser=argparse.ArgumentParser()
    parser.add_argument("--preflight",action="store_true")
    parser.add_argument("--duration",type=int,default=15000)
    args=parser.parse_args()
    if not 1<=args.duration<=18000:
        raise ValueError("duration out of bounds")
    client=Runner()
    check=client.post("/runner/preflight")
    if check.get("authenticated") is not True or check.get("owner_oauth_configured") is not True:
        raise RuntimeError("relay preflight denied")
    print("WORKERS_LIVE_PREFLIGHT_VERIFIED",flush=True)
    if args.preflight:
        return
    proof=verify_upstream()
    if not proof.get("verified") or proof.get("matching_local_fixtures")!=1:
        raise RuntimeError("official Studio local fixture not verified")
    print("WORKERS_LOCAL_OFFICIAL_STUDIO_MCP_VERIFIED",flush=True)
    end=time.monotonic()+args.duration
    errors=0
    ready=False
    while time.monotonic()<end:
        try:
            job=client.post("/runner/poll")
            if not ready:
                print("WORKERS_RELAY_READY",flush=True)
                ready=True
            result=execute_job(job)
            if result is not None:
                ack=client.post("/runner/result",result)
                if ack.get("accepted") is not True:
                    raise RuntimeError("result not accepted")
                print("WORKERS_RELAY_READONLY_RESULT_ACCEPTED",flush=True)
            errors=0
        except Exception:
            errors+=1
            print("WORKERS_RELAY_RETRY: classified failure; sensitive details omitted",flush=True)
            if errors>=5:
                raise RuntimeError("relay repeatedly unavailable") from None
        time.sleep(5 if errors==0 else min(30,5*errors))

if __name__=="__main__":
    try:
        main()
    except Exception:
        raise SystemExit("WORKERS_RELAY_FAILED: no credentials or raw response logged") from None
