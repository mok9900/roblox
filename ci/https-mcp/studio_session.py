"""Persistent official Studio MCP session; staged development transport.

Only the exact CI-local fixture is exposed. Tool discovery uses the official
catalog; external/account-wide tools require a future separate authorization.
No automatic replay of mutations. Do not log raw RPC results.
"""
import json
import os
import time
from pathlib import Path
from bridge import Child, ROOT, FIXTURE, local_fixture_count, proof_shape

READ = frozenset(("list_roblox_studios","get_studio_state","search_game_tree",
    "inspect_instance","script_search","script_read","script_grep",
    "get_console_output","screen_capture","list_skills","skill"))
EDIT = frozenset(("multi_edit","save_place","start_stop_play","user_mouse_input",
    "user_keyboard_input","character_navigation","generate_procedural_model"))
# Tools with account/network/asset/code-execution effects are intentionally
# not authorized by enabling local edits. Each requires its own policy.
EXTERNAL = frozenset(("execute_luau","open_cloud_invoke","upload_image","store_image",
    "http_get","search_asset","insert_asset","generate_scene","generate_mesh",
    "generate_material","generate_texture","generate_avatar","generate_animation",
    "segment_mesh","auto_setup_avatar","wait_job_finished","create_skill","edit_skill",
    "subagent","submit_feedback"))

def proof_payload(result):
    if not isinstance(result,dict) or result.get("isError"):
        raise RuntimeError("official list failed")
    return result.get("structuredContent",result)

def fixture_records(value,depth=0):
    if depth>12:
        return []
    if isinstance(value,str):
        try: return fixture_records(json.loads(value),depth+1)
        except (ValueError,RecursionError): return []
    if isinstance(value,list):
        return [r for item in value[:100] for r in fixture_records(item,depth+1)]
    if not isinstance(value,dict):
        return []
    if local_fixture_count({k:value[k] for k in ("name","file","persistedToCloud") if k in value})==1:
        return [value]
    return [r for k in ("studios","instances","content","structuredContent","text","result")
            if k in value for r in fixture_records(value[k],depth+1)]

def official_argv():
    if os.name!="nt" or os.getenv("GITHUB_ACTIONS")!="true" or os.getenv("RUNNER_OS")!="Windows":
        raise RuntimeError("GitHub-hosted Windows required")
    if not (Path(os.environ["LOCALAPPDATA"])/"Roblox"/"mcp.bat").is_file() or not (ROOT/"roblox-mcp-stdio.cmd").is_file():
        raise RuntimeError("official launcher missing")
    return ["cmd.exe","/d","/c","roblox-mcp-stdio.cmd"]

class StudioSession:
    def __init__(self,argv=None,allow_local_edits=False,child_factory=Child):
        self.live=argv is None
        self.argv=official_argv() if self.live else argv
        self.child=None
        self.child_factory=child_factory
        self.catalog={}
        self.allowed=READ | (EDIT if allow_local_edits else frozenset())

    def __enter__(self):
        try:
            self.child=self.child_factory(self.argv)
            init=self.child.send("initialize",{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"roblox-ci-session","version":"0.2.0"}})
            if not isinstance(init,dict) or not isinstance(init.get("protocolVersion"),str):
                raise RuntimeError("invalid initialization")
            self.child.send("notifications/initialized",notification=True)
            cursor=None
            seen=set()
            for _ in range(10):
                result=self.child.send("tools/list",{"cursor":cursor} if cursor else {})
                if not isinstance(result,dict) or not isinstance(result.get("tools"),list):
                    raise RuntimeError("invalid catalog")
                for tool in result["tools"]:
                    if not isinstance(tool,dict) or not isinstance(tool.get("name"),str) or not isinstance(tool.get("inputSchema"),dict):
                        raise RuntimeError("invalid catalog entry")
                    name=tool["name"]
                    if name in self.catalog:
                        raise RuntimeError("duplicate tool")
                    self.catalog[name]=tool
                cursor=result.get("nextCursor")
                if not cursor: break
                if not isinstance(cursor,str) or cursor in seen:
                    raise RuntimeError("invalid catalog cursor")
                seen.add(cursor)
            else: raise RuntimeError("catalog too large")
            if "list_roblox_studios" not in self.catalog:
                raise RuntimeError("official discovery unavailable")
            return self
        except BaseException:
            self.close()
            raise

    def close(self):
        child,self.child=self.child,None
        self.catalog={}
        if child: child.close()

    def __exit__(self,*args):
        self.close()

    def discover(self):
        if not self.child: raise RuntimeError("session closed")
        result=self.child.send("tools/call",{"name":"list_roblox_studios","arguments":{}})
        payload=proof_payload(result)
        count=local_fixture_count(payload)
        if self.live:
            print("OFFICIAL_STUDIO_PROOF_SHAPE="+json.dumps(proof_shape(payload),sort_keys=True),flush=True)
        return count,fixture_records(payload)

    def verify(self,startup_wait=0):
        deadline=time.monotonic()+min(60,max(0,startup_wait))
        while True:
            count,_=self.discover()
            if count!=0 or time.monotonic()>=deadline:
                return {"verified":count==1,"matching_local_fixtures":count,"source":"official_studio_mcp"}
            time.sleep(min(5,max(0,deadline-time.monotonic())))

    def visible_catalog(self):
        return [self.catalog[name] for name in sorted(self.allowed & self.catalog.keys())]

    def invoke(self,name,args):
        if name not in self.allowed or name not in self.catalog or not isinstance(args,dict):
            raise ValueError("tool denied")
        if len(json.dumps(args,ensure_ascii=False).encode())>65536:
            raise ValueError("arguments too large")
        count,records=self.discover()
        if count!=1 or len(records)!=1:
            raise RuntimeError("local fixture unavailable or ambiguous")
        record=records[0]
        studio_id=record.get("id")
        if not isinstance(studio_id,str) or not studio_id:
            raise RuntimeError("fixture has no verified studio ID")
        if name=="list_roblox_studios":
            if args: raise ValueError("unexpected arguments")
            # Return only the verified local fixture, not other account games.
            data={k:record[k] for k in ("id","name","mode","state","persistedToCloud") if k in record}
            return {"content":[{"type":"text","text":json.dumps({"studios":[data]})}],"structuredContent":{"studios":[data]}}
        if args.get("studio_id")!=studio_id:
            raise ValueError("wrong or stale studio ID")
        # Revalidated exact local identity immediately before every call.
        result=self.child.send("tools/call",{"name":name,"arguments":args})
        if not isinstance(result,dict):
            raise RuntimeError("invalid tool response")
        return result
