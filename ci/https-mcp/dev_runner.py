"""Finite, explicitly started development session with a 30-minute handoff.

No permanent schedule; at most 24 hours from the first ready runner.
Read-only rolling until durable place checkpoint transfer is implemented.
"""
import argparse
import json
import os
import time
import urllib.request
import uuid
from runner import Runner, OPENER, hosted_only
from studio_session import StudioSession

WORKFLOW="https://api.github.com/repos/mok9900/roblox/actions/workflows/roblox-workers-relay-live.yml/dispatches"
OVERLAP_MS=1800000
RUN_MS=15000000
MAX_HOP=7

def now_ms():
    return int(time.time()*1000)

def session_plan(hours,sid,end,hop,edits,now):
    if not 1<=hours<=24 or not 0<=hop<=MAX_HOP:
        raise ValueError("invalid development duration or hop")
    if edits and hours>4:
        raise ValueError("rolling edits require durable checkpoint transfer")
    if hop==0:
        if sid or end: raise ValueError("initial session has no predecessor")
        sid=str(uuid.uuid4())
        end=now+hours*3600000
    elif not sid or str(uuid.UUID(sid))!=sid or not now<end<=now+hours*3600000 or edits:
        raise ValueError("invalid or expired successor session")
    return {"session_id":sid,"session_end":end,"deadline":min(end,now+RUN_MS),
            "hop":hop,"hours":hours,"allow_edits":edits}

def successor_payload(plan):
    if plan["allow_edits"] or plan["hop"]>=MAX_HOP or plan["deadline"]>=plan["session_end"]:
        return None
    return {"ref":"main","inputs":{"windows_runner":"windows-2022","dev_hours":str(plan["hours"]),
        "dev_session_id":plan["session_id"],"dev_session_end":str(plan["session_end"]),
        "dev_hop":str(plan["hop"]+1),"dev_allow_local_edits":"false"}}

def start_successor(plan):
    payload=successor_payload(plan)
    if payload is None:return False
    request=urllib.request.Request(WORKFLOW,data=json.dumps(payload).encode(),method="POST",
        headers={"Authorization":"Bearer "+os.environ["GH_TOKEN"],"Accept":"application/vnd.github+json",
                 "Content-Type":"application/json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"roblox-ci-dev/0.2"})
    with OPENER.open(request,timeout=25) as response:
        if response.status not in (200,204):
            raise RuntimeError("successor dispatch rejected")
    return True

def mcp_error(message):
    return {"content":[{"type":"text","text":message}],"isError":True}

def execute(job,session):
    rid=job.get("request_id")
    if not isinstance(rid,str) or str(uuid.UUID(rid))!=rid or type(job.get("generation")) is not int:
        raise ValueError("invalid fenced request")
    a=job.get("action")
    if not isinstance(a,dict) or not isinstance(a.get("name"),str) or not isinstance(a.get("arguments"),dict):
        raise ValueError("invalid action")
    try:
        if a["name"]=="verify_ci_studio":
            if a["arguments"]:raise ValueError("unexpected arguments")
            proof=session.verify()
            result={"content":[{"type":"text","text":json.dumps(proof)}],"isError":not proof["verified"]}
        else:
            result=session.invoke(a["name"],a["arguments"])
        if not isinstance(result,dict) or not isinstance(result.get("content"),list) or len(json.dumps(result,ensure_ascii=False).encode())>59000:
            result=mcp_error("Result exceeds supported size or format; outcome may be unknown.")
    except Exception:
        result=mcp_error("Official Studio request failed or target unavailable. Do not replay edits automatically.")
    return {"request_id":rid,"generation":job["generation"],"result":result}

def main():
    hosted_only()
    p=argparse.ArgumentParser()
    p.add_argument("--validate-only",action="store_true")
    args=p.parse_args()
    hours=int(os.environ.get("RS_DEV_HOURS","0"))
    sid=os.environ.get("RS_DEV_SESSION_ID","")
    end=int(os.environ.get("RS_DEV_SESSION_END","") or 0)
    hop=int(os.environ.get("RS_DEV_HOP","") or 0)
    edits=os.environ.get("RS_DEV_ALLOW_EDITS","false").lower()=="true"
    session_plan(hours,sid,end,hop,edits,now_ms())
    if args.validate_only:return
    client=Runner()
    with StudioSession(allow_local_edits=edits) as session:
        proof=session.verify(startup_wait=60)
        if not proof["verified"]:raise RuntimeError("official fixture unavailable")
        session.invoke("list_roblox_studios",{})
        plan=session_plan(hours,sid,end,hop,edits,now_ms())
        registration={k:plan[k] for k in ("session_id","session_end","deadline","allow_edits")}
        registration.update(proof=proof,catalog=session.visible_catalog())
        if client.post("/development/register",registration).get("registered") is not True:
            raise RuntimeError("development registration failed")
        print("RS_DEVELOPMENT_REGISTERED",flush=True)
        dispatched=False
        errors=0
        while now_ms()<plan["deadline"]:
            try:
                job=client.post("/development/poll",{"session_id":plan["session_id"]})
                role=job.get("role")
                if role=="retired":
                    print("RS_HANDOFF_COMPLETE",flush=True)
                    return
                if role not in ("active","standby"):raise RuntimeError("invalid role")
                if job.get("request_id") is not None:
                    if role!="active":raise RuntimeError("standby received work")
                    result=execute(job,session)
                    if client.post("/development/result",result).get("accepted") is not True:
                        raise RuntimeError("result not accepted")
                    print("RS_DEVELOPMENT_RESULT_ACCEPTED",flush=True)
                if role=="active" and not dispatched and now_ms()>=plan["deadline"]-OVERLAP_MS and successor_payload(plan):
                    dispatched=True
                    try:
                        if start_successor(plan):print("RS_SUCCESSOR_DISPATCHED",flush=True)
                    except Exception:
                        # An ambiguous dispatch response must not create another job.
                        print("RS_SUCCESSOR_DISPATCH_UNCONFIRMED",flush=True)
                errors=0
            except Exception:
                errors+=1
                print("RS_DEVELOPMENT_RELAY_FAILURE",flush=True)
                if errors>=5:raise RuntimeError("development relay unavailable") from None
            time.sleep(5)
        print("RS_DEVELOPMENT_DEADLINE_REACHED",flush=True)

if __name__=="__main__":
    try: main()
    except Exception: raise SystemExit("RS_DEVELOPMENT_FAILED: details withheld") from None
