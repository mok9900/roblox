"""Synthetic stdio test server only. No Roblox APIs, accounts or credentials."""
import json
import sys
for line in sys.stdin:
    req=json.loads(line)
    if "id" not in req:
        continue
    method=req.get("method")
    if method=="initialize":
        result={"protocolVersion":"2025-06-18","capabilities":{"tools":{}},"serverInfo":{"name":"synthetic-test-only","version":"0.0.1"}}
    elif method=="tools/list":
        result={"tools":[{"name":"list_roblox_studios","description":"Synthetic fixture only","inputSchema":{"type":"object"}}]}
    elif method=="tools/call" and req.get("params",{}).get("name")=="list_roblox_studios":
        result={"content":[{"type":"text","text":json.dumps({"studios":[{"name":"ci_only_baseplate_test","persistedToCloud":False},{"name":"synthetic-cloud","persistedToCloud":True}]})}]}
    else:
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"error":{"code":-32601,"message":"unknown"}}),flush=True)
        continue
    print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":result}),flush=True)
