// Private owner-authenticated MCP relay; v1 proof plus bounded v2 development sessions.
import {DevelopmentBroker} from "./development_broker.mjs";
const HOST = "roblox-mcp.parcel-mcp-seojun.workers.dev";
const URL_BASE = "https://" + HOST;
const GH_ISSUER = "https://token.actions.githubusercontent.com";
const GH_AUD = URL_BASE + "/runner";
const REPO = "mok9900/roblox";
const REPO_ID = "911533556";
const PROBE = REPO + "/.github/workflows/roblox-workers-relay-test.yml@refs/heads/main";
const LIVE = REPO + "/.github/workflows/roblox-workers-relay-live.yml@refs/heads/main";
const TOOL = {name:"verify_ci_studio",description:"Read-only live proof of the official Studio MCP on the GitHub-hosted Windows runner; does not edit or publish.",inputSchema:{type:"object",properties:{},additionalProperties:false},annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false}};
const keys = new Map();
const decoder = new TextDecoder("utf-8",{fatal:true});
function json(data,status=200) {
  return new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
}
function b64(s) {
  if (!/^[A-Za-z0-9_-]+$/.test(s)) throw Error("bad base64url");
  return Uint8Array.from(atob(s.replace(/-/g,"+").replace(/_/g,"/").padEnd(Math.ceil(s.length/4)*4,"=")),c=>c.charCodeAt(0));
}
async function jwks(uri,refresh=false) {
  const cached=keys.get(uri);
  if (!refresh && cached && Date.now()<cached.until) return cached.value;
  let r;try{r=await fetch(uri,{redirect:"follow",headers:{Accept:"application/json","User-Agent":"roblox-mcp-relay/0.1"},signal:AbortSignal.timeout(10000)});}catch{throw Error("key fetch failed");}
  if(r.url && new URL(r.url).origin!==new URL(uri).origin)throw Error("key redirect denied");
  if (!r.ok) throw Error("key service unavailable");
  let v;try{v=await r.json();}catch{throw Error("key decode failed");}
  if (!Array.isArray(v.keys)||v.keys.length>100) throw Error("key set invalid");
  keys.set(uri,{value:v.keys,until:Date.now()+300000});
  return v.keys;
}
export async function verifyJwt(token,issuer,audience,keyUri) {
  if (!token || token.length>16384 || typeof audience!=="string" || !audience) throw Error("auth required");
  const parts=token.split(".");
  if(parts.length!==3) throw Error("jwt invalid");
  let header,payload;try{header=JSON.parse(decoder.decode(b64(parts[0])));payload=JSON.parse(decoder.decode(b64(parts[1])));}catch{throw Error("token decode failed");}
  if(header.alg!=="RS256"||typeof header.kid!=="string"||!header.kid||header.crit!==undefined) throw Error("alg invalid");
  let k=(await jwks(keyUri)).find(x=>x.kid===header.kid&&x.kty==="RSA"&&(!x.alg||x.alg==="RS256")&&(!x.use||x.use==="sig"));
  if(!k) {
    k=(await jwks(keyUri,true)).find(x=>x.kid===header.kid&&x.kty==="RSA"&&(!x.alg||x.alg==="RS256")&&(!x.use||x.use==="sig"));
  }
  if(!k) throw Error("key not found");
  let key;try{key=await crypto.subtle.importKey("jwk",{kty:"RSA",n:k.n,e:k.e,alg:"RS256",ext:true},{name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["verify"]);}catch{throw Error("key import failed");}
  let valid;try{valid=await crypto.subtle.verify("RSASSA-PKCS1-v1_5",key,b64(parts[2]),new TextEncoder().encode(parts[0]+"."+parts[1]));}catch{throw Error("signature verification failed");}
  if(!valid) throw Error("signature invalid");
  const now=Math.floor(Date.now()/1000);
  const aud=Array.isArray(payload.aud)?payload.aud:[payload.aud];
  if(payload.iss!==issuer||!aud.includes(audience)||!Number.isFinite(payload.exp)||payload.exp<=now||!Number.isFinite(payload.iat)||payload.iat>now+30||(payload.nbf!==undefined&&(!Number.isFinite(payload.nbf)||payload.nbf>now+30))) throw Error("claims invalid");
  return payload;
}
export function runnerIdentity(p,probe=false) {
  const workflow=probe?PROBE:LIVE;
  if(p.repository!==REPO||String(p.repository_id)!==REPO_ID||p.ref!=="refs/heads/main"||p.runner_environment!=="github-hosted"||p.workflow_ref!==workflow||!["push","workflow_dispatch"].includes(p.event_name)) throw Error("workflow denied");
  if(!/^\d+$/.test(String(p.run_id))||!/^\d+$/.test(String(p.run_attempt))) throw Error("run identity invalid");
  return String(p.run_id)+":"+String(p.run_attempt);
}
async function runnerAuth(req,probe,development=false) {
  const auth=req.headers.get("Authorization")||"";
  if(!auth.startsWith("Bearer ")) throw Error("auth required");
  const p=await verifyJwt(auth.slice(7),GH_ISSUER,GH_AUD,GH_ISSUER+"/.well-known/jwks");
  if(development&&p.event_name!=="workflow_dispatch")throw Error("workflow denied");
  return runnerIdentity(p,probe);
}
function accessConfigured(env) {
  return /^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com$/.test(env.CF_ACCESS_ISSUER||"")&&!!env.CF_ACCESS_AUD&&!!env.CF_ACCESS_ALLOWED_EMAIL;
}
async function ownerAuth(req,env) {
  if(!accessConfigured(env)) return false;
  const p=await verifyJwt(req.headers.get("Cf-Access-Jwt-Assertion"),env.CF_ACCESS_ISSUER,env.CF_ACCESS_AUD,env.CF_ACCESS_ISSUER+"/cdn-cgi/access/certs");
  return typeof p.email==="string"&&p.email.toLowerCase()===env.CF_ACCESS_ALLOWED_EMAIL.toLowerCase();
}
async function readBody(req) {
  if(!(req.headers.get("content-type")||"").toLowerCase().startsWith("application/json")) throw Error("bad content type");
  const stream=req.body?.getReader();
  if(!stream) throw Error("empty body");
  const chunks=[];let total=0;
  while(true) {
    const {done,value}=await stream.read();if(done)break;
    total+=value.byteLength;
    if(total>65536){await stream.cancel();throw Error("body too large");}
    chunks.push(value);
  }
  const bytes=new Uint8Array(total);let offset=0;
  for(const c of chunks){bytes.set(c,offset);offset+=c.byteLength;}
  return JSON.parse(decoder.decode(bytes));
}
export function validResult(x) {
  return x&&typeof x.verified==="boolean"&&Number.isSafeInteger(x.matching_local_fixtures)&&x.matching_local_fixtures>=0&&x.matching_local_fixtures<=100&&x.verified===(x.matching_local_fixtures===1)&&x.source==="official_studio_mcp";
}
async function rpc(req,env) {
  let m;
  try{m=await readBody(req);}catch{return json({error:"Invalid body"},400);}
  if(!m||Array.isArray(m)||m.jsonrpc!=="2.0"||typeof m.method!=="string") return json({jsonrpc:"2.0",id:null,error:{code:-32600,message:"Invalid request"}});
  if(!Object.hasOwn(m,"id")) return new Response(null,{status:202});
  if(!["string","number"].includes(typeof m.id)&&m.id!==null) return json({error:"Invalid id"},400);
  const ok=result=>json({jsonrpc:"2.0",id:m.id,result});
  const err=(code,message)=>json({jsonrpc:"2.0",id:m.id,error:{code,message}});
  const p=m.params??{};
  if(!p||typeof p!=="object"||Array.isArray(p)) return err(-32602,"Invalid params");
  if(m.method==="initialize") {
    const supported=["2025-03-26","2025-06-18","2025-11-25"];
    return ok({protocolVersion:supported.includes(p.protocolVersion)?p.protocolVersion:"2025-11-25",capabilities:{tools:{listChanged:false}},serverInfo:{name:"roblox-workers-relay",version:"0.1.0"}});
  }
  if(m.method==="ping")return ok({});
  const dev=env.RELAY.get(env.RELAY.idFromName("development-v2"));
  let catalog=[];
  try{
    const d=await dev.fetch("https://relay.internal/development/catalog",{method:"POST"});
    if(d.ok){const c=await d.json();if(Array.isArray(c.tools))catalog=c.tools;}
  }catch{}
  const listTool={name:"list_studio_tools",description:"List the native tools of the active verified local Studio development session.",inputSchema:{type:"object",properties:{},additionalProperties:false},annotations:{readOnlyHint:true}};
  const callTool={name:"call_studio_tool",description:"Invoke a discovered native tool on the exact local Studio fixture. Requires the current Studio ID where the native schema requires it. Edits require explicit local-edit session opt-in.",inputSchema:{type:"object",properties:{name:{type:"string"},arguments:{type:"object"}},required:["name","arguments"],additionalProperties:false}};
  if(m.method==="tools/list")return ok({tools:catalog.length?[TOOL,listTool,callTool,...catalog]:[TOOL]});
  if(m.method!=="tools/call")return err(-32601,"Method not found");
  if(p.name==="list_studio_tools"){
    if(JSON.stringify(p.arguments??{})!=="{}")return err(-32602,"Invalid arguments");
    return ok({content:[{type:"text",text:JSON.stringify({tools:catalog})}],isError:!catalog.length});
  }
  let action={name:p.name,arguments:p.arguments??{}};
  if(p.name==="call_studio_tool"){
    if(!p.arguments||typeof p.arguments!=="object"||Array.isArray(p.arguments)||Object.keys(p.arguments).sort().join(",")!=="arguments,name")return err(-32602,"Invalid arguments");
    action=p.arguments;
  }
  if(!action.arguments||typeof action.arguments!=="object"||Array.isArray(action.arguments))return err(-32602,"Invalid arguments");
  if(action.name===TOOL.name&&JSON.stringify(action.arguments)!=="{}")return err(-32602,"Invalid arguments");
  if(catalog.length){
    if(action.name!==TOOL.name&&!catalog.some(t=>t.name===action.name))return err(-32602,"Tool denied");
    try{
      const r=await dev.fetch("https://relay.internal/development/request",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(action)});
      if(!r.ok)return ok({content:[{type:"text",text:"Development request unavailable, busy, or outcome unknown. Do not automatically replay mutations."}],isError:true});
      const v=await r.json();
      if(!v.result||!Array.isArray(v.result.content))throw Error("invalid tool result");
      return ok(v.result);
    }catch{return ok({content:[{type:"text",text:"Development request failed; outcome unknown."}],isError:true});}
  }
  if(action.name!==TOOL.name||p.name!==TOOL.name)return err(-32602,"Development runner unavailable or tool denied");
  const unavailable=()=>ok({content:[{type:"text",text:"Live CI Studio verification unavailable; no connection claimed."}],isError:true});
  try{
    const broker=env.RELAY.get(env.RELAY.idFromName("single-ci"));
    const r=await broker.fetch("https://relay.internal/request",{method:"POST"});
    if(!r.ok)return unavailable();
    const v=await r.json();
    if(!validResult(v))return unavailable();
    return ok({content:[{type:"text",text:JSON.stringify(v)}],isError:!v.verified});
  }catch{return unavailable();}
}
export default {
  async fetch(req,env) {
    const u=new URL(req.url);
    if(u.hostname!==HOST||u.protocol!=="https:"||u.search)return json({error:"Not found"},404);
    if(u.pathname==="/mcp") {
      if(!accessConfigured(env))return json({error:"Owner OAuth is not configured"},503);
      const origin=req.headers.get("Origin");
      if(origin&&origin!=="https://chatgpt.com"&&origin!==URL_BASE)return json({error:"Origin denied"},403);
      try{if(!await ownerAuth(req,env))return json({error:"Unauthorized"},401);}catch{return json({error:"Unauthorized"},401);}
      if(req.method!=="POST")return json({error:"Method not allowed"},405);
      return rpc(req,env);
    }
    const development=["/development/register","/development/poll","/development/result"].includes(u.pathname);
    if((!development&&!["/runner/probe","/runner/preflight","/runner/poll","/runner/result"].includes(u.pathname))||req.method!=="POST")return json({error:"Not found"},404);
    let id;
    try{id=await runnerAuth(req,u.pathname==="/runner/probe",development);}catch(e){const reason=["auth required","jwt invalid","alg invalid","key service unavailable","key fetch failed","key redirect denied","key decode failed","token decode failed","key import failed","signature verification failed","key set invalid","key not found","signature invalid","claims invalid","workflow denied","run identity invalid"].includes(e?.message)?e.message:"verification error";return json({error:"Unauthorized",...(u.pathname==="/runner/probe"?{reason}: {})},401);}
    if(u.pathname==="/runner/probe"||u.pathname==="/runner/preflight")return json({authenticated:true,owner_oauth_configured:accessConfigured(env),scope:u.pathname==="/runner/probe"?"github-hosted-readonly-probe":"github-hosted-readonly-live"});
    if(!accessConfigured(env))return json({error:"Owner OAuth not configured"},503);
    let body={};
    if(development||u.pathname.endsWith("/result")){try{body=await readBody(req);}catch{return json({error:"Invalid result"},400);}}
    const broker=env.RELAY.get(env.RELAY.idFromName(development?"development-v2":"single-ci"));
    return broker.fetch("https://relay.internal"+u.pathname,{method:"POST",headers:{"Content-Type":"application/json","X-Verified-Runner":id},body:JSON.stringify(body)});
  }
};
export class Relay {
  constructor(){this.active=null;this.lastRunner=null;this.development=new DevelopmentBroker();}
  async fetch(req) {
    const path=new URL(req.url).pathname;
    if(req.method!=="POST")return json({error:"Method not allowed"},405);
    if(path.startsWith("/development/")){
      let v;const id=req.headers.get("X-Verified-Runner");
      if(path==="/development/catalog")v=this.development.catalog();
      else if(path==="/development/request")v=await this.development.request(await req.json());
      else if(!id)return json({error:"Unauthorized"},401);
      else if(path==="/development/register")v=this.development.register(id,await req.json());
      else if(path==="/development/poll")v=this.development.poll(id,await req.json());
      else if(path==="/development/result")v=this.development.result(id,await req.json());
      else return json({error:"Not found"},404);
      return json(v.value,v.status);
    }
    if(path==="/request"){
      if(!this.lastRunner||Date.now()-this.lastRunner.at>20000)return json({error:"Runner unavailable"},503);
      if(this.active)return json({error:"Busy"},409);
      const id=crypto.randomUUID();
      return new Promise(resolve=>{
        const timeout=setTimeout(()=>{if(this.active?.id===id)this.active=null;resolve(json({error:"Timeout"},504));},60000);
        this.active={id,runner:this.lastRunner.id,delivered:false,finish:r=>{clearTimeout(timeout);this.active=null;resolve(r);}};
      });
    }
    const runner=req.headers.get("X-Verified-Runner");
    if(!runner)return json({error:"Unauthorized"},401);
    if(path==="/runner/poll"){
      if(this.lastRunner&&this.lastRunner.id!==runner&&Date.now()-this.lastRunner.at<20000)return json({error:"Runner already active"},409);
      this.lastRunner={id:runner,at:Date.now()};
      const a=this.active;
      if(a&&a.runner===runner&&!a.delivered){a.delivered=true;return json({request_id:a.id,action:"verify_ci_studio"});}
      return json({request_id:null});
    }
    if(path==="/runner/result"){
      const b=await req.json(),a=this.active;
      if(!a||a.runner!==runner||!a.delivered||a.id!==b.request_id)return json({error:"Stale request"},409);
      if(!validResult(b.result))return json({error:"Invalid proof"},400);
      a.finish(json({verified:b.result.verified,matching_local_fixtures:b.result.matching_local_fixtures,source:"official_studio_mcp"}));
      return json({accepted:true});
    }
    return json({error:"Not found"},404);
  }
}
