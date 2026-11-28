import test from "node:test";
import assert from "node:assert/strict";
import {Relay, validResult, runnerIdentity} from "./worker.mjs";

const proof={verified:true,matching_local_fixtures:1,source:"official_studio_mcp"};
const call=(relay,path,runner,body)=>relay.fetch(new Request("https://relay.internal"+path,{method:"POST",headers:{"Content-Type":"application/json",...(runner?{"X-Verified-Runner":runner}:{})},...(body?{body:JSON.stringify(body)}:{})}));

test("proof requires exact type, count and source",()=>{
  assert.equal(validResult(proof),true);
  assert.equal(validResult({...proof,matching_local_fixtures:2}),false);
  assert.equal(validResult({...proof,verified:"true"}),false);
  assert.equal(validResult({...proof,source:"fixture"}),false);
  assert.equal(validResult({...proof,verified:false,matching_local_fixtures:0}),true);
});

test("runner identity requires exact repo ID, workflow and hosted runner",()=>{
  const p={repository:"mok9900/roblox",repository_id:"911533556",ref:"refs/heads/main",runner_environment:"github-hosted",workflow_ref:"mok9900/roblox/.github/workflows/roblox-workers-relay-live.yml@refs/heads/main",event_name:"push",run_id:"100",run_attempt:"1"};
  assert.equal(runnerIdentity(p),"100:1");
  for(const change of [{repository_id:"123"},{runner_environment:"self-hosted"},{ref:"refs/heads/other"},{workflow_ref:"other"},{event_name:"pull_request"}]){
    assert.throws(()=>runnerIdentity({...p,...change}));
  }
});

test("offline, unauthorized, and stale responses fail closed",async()=>{
  const r=new Relay();
  assert.equal((await call(r,"/request")).status,503);
  assert.equal((await call(r,"/runner/poll")).status,401);
  assert.equal((await call(r,"/runner/result","1:1",{request_id:"unknown",result:proof})).status,409);
});

test("authenticated relay routes one request and accepts only matching proof",async()=>{
  const r=new Relay(), first="100:1", other="200:1";
  assert.deepEqual(await (await call(r,"/runner/poll",first)).json(),{request_id:null});
  assert.equal((await call(r,"/runner/poll",other)).status,409);
  const pending=call(r,"/request");
  assert.equal((await call(r,"/request")).status,409);
  const job=await (await call(r,"/runner/poll",first)).json();
  assert.equal(job.action,"verify_ci_studio");
  assert.match(job.request_id,/^[0-9a-f-]{36}$/);
  assert.deepEqual(await (await call(r,"/runner/poll",first)).json(),{request_id:null});
  assert.equal((await call(r,"/runner/result",other,{request_id:job.request_id,result:proof})).status,409);
  assert.equal((await call(r,"/runner/result",first,{request_id:job.request_id,result:{...proof,matching_local_fixtures:0}})).status,400);
  assert.equal((await call(r,"/runner/result",first,{request_id:job.request_id,result:proof})).status,200);
  assert.deepEqual(await (await pending).json(),proof);
  assert.equal((await call(r,"/runner/result",first,{request_id:job.request_id,result:proof})).status,409);
});

import {HandoffModel} from "./handoff-model.mjs";

function scenario(){
  let t=0;
  const m=new HandoffModel({now:()=>t,sessionEnd:7200000});
  assert.equal(m.admit("100:1",3600000,proof),true);
  return {m,at:(v)=>{t=v;}};
}
test("bounded handoff admits a verified successor only in the overlap window",()=>{
  const {m,at}=scenario();
  at(1799999);
  assert.equal(m.admit("200:1",7200000,proof),false);
  at(1800000);
  assert.equal(m.admit("200:1",7200000,{...proof,verified:false,matching_local_fixtures:0}),false);
  assert.equal(m.admit("200:1",7200000,proof),true);
  assert.equal(m.admit("300:1",7200000,proof),false);
  assert.equal(m.heartbeat("100:1"),true);
  assert.equal(m.begin("r1").runner,"100:1");
  assert.equal(m.promote(),false);
  assert.equal(m.finish("200:1","r1",1),false);
  assert.equal(m.finish("100:1","r1",1),true);
  assert.equal(m.promote(),true);
  assert.equal(m.heartbeat("100:1"),false);
  assert.deepEqual(m.begin("r2"),{requestId:"r2",runner:"200:1",generation:2});
  assert.equal(m.finish("100:1","r2",1),false);
  assert.equal(m.finish("200:1","r2",2),true);
});
test("stale successor cannot take traffic; old runner remains available",()=>{
  const {m,at}=scenario();
  at(1800000);
  assert.equal(m.admit("200:1",7200000,proof),true);
  at(1820001);m.heartbeat("100:1");
  assert.equal(m.promote(),false);
  assert.equal(m.begin("r").runner,"100:1");
});
test("session expiry and ambiguous requests fail closed",()=>{
  const {m,at}=scenario();
  at(1800000);m.heartbeat("100:1");
  assert.equal(m.admit("200:1",7200001,proof),false);
  assert.equal(m.admit("200:1",7200000,proof),true);
  const old=m.begin("old");
  assert.equal(m.promote(),false);
  assert.equal(m.abandon("old",old.generation),true);
  assert.equal(m.promote(),true);
  assert.equal(m.finish("100:1","old",old.generation),false);
  at(7200000);
  assert.equal(m.begin("new"),null);
  assert.equal(m.heartbeat("200:1"),false);
  assert.equal(m.admit("300:1",7300000,proof),false);
});

import {DevelopmentBroker} from "./development_broker.mjs";
const sid="12345678-1234-4234-9234-123456789012";
const cat=[{name:"list_roblox_studios",inputSchema:{type:"object"}},{name:"get_studio_state",inputSchema:{type:"object"}}];
function devScenario(){
  let t=1000;
  const b=new DevelopmentBroker({now:()=>t,requestTimeout:1000});
  const reg={session_id:sid,session_end:7201000,deadline:3601000,allow_edits:false,proof,catalog:cat};
  assert.equal(b.register("100:1",reg).status,200);
  return {b,reg,at:v=>{t=v;}};
}
test("development broker requires live proof and separately authenticated workflow",()=>{
  const p={repository:"mok9900/roblox",repository_id:"911533556",ref:"refs/heads/main",runner_environment:"github-hosted",workflow_ref:"mok9900/roblox/.github/workflows/roblox-workers-relay-dev.yml@refs/heads/main",event_name:"workflow_dispatch",run_id:"100",run_attempt:"1"};
  assert.equal(runnerIdentity(p,false,true),"100:1");
  assert.throws(()=>runnerIdentity({...p,event_name:"push"},false,true));
  assert.throws(()=>runnerIdentity(p));
  const {b,reg,at}=devScenario();
  at(1801000);
  assert.equal(b.register("200:1",{...reg,deadline:7201000,proof:{...proof,verified:false}}).status,400);
  assert.equal(b.register("200:1",{...reg,deadline:7201000,catalog:[...cat,{name:"open_cloud_invoke",inputSchema:{type:"object"}}]}).status,400);
});
test("real broker handoff drains old request and fences late results",async()=>{
  const {b,reg,at}=devScenario();
  at(1800999);b.poll("100:1",{session_id:sid});
  assert.equal(b.register("200:1",{...reg,deadline:7201000}).status,409);
  at(1801000);b.poll("100:1",{session_id:sid});
  const pending=b.request({name:"get_studio_state",arguments:{studio_id:"old"}});
  const job=b.poll("100:1",{session_id:sid}).value;
  assert.equal(job.action.name,"get_studio_state");
  assert.equal(b.register("200:1",{...reg,deadline:7201000}).status,200);
  assert.equal(b.poll("200:1",{session_id:sid}).value.role,"standby");
  const result={request_id:job.request_id,generation:job.generation,result:{content:[{type:"text",text:"ok"}]}};
  assert.equal(b.result("200:1",result).status,409);
  assert.equal(b.result("100:1",result).status,200);
  assert.equal((await pending).status,200);
  assert.equal(b.poll("100:1",{session_id:sid}).value.role,"retired");
  assert.equal(b.poll("200:1",{session_id:sid}).value.role,"active");
  assert.equal(b.result("100:1",result).status,409);
  assert.equal(b.request({name:"execute_luau",arguments:{}}).status,403);
});
test("finite development session expires and cannot accept another session early",()=>{
  const {b,reg,at}=devScenario();
  assert.equal(b.register("200:1",{...reg,session_id:"22345678-1234-4234-9234-123456789012"}).status,409);
  at(7201000);
  assert.equal(b.catalog().status,503);
  assert.equal(b.poll("100:1",{session_id:sid}).status,410);
});

import {DurableDevelopmentRelay} from "./development_broker.mjs";
class MemoryStorage {
  constructor(initial){this.value=initial===undefined?undefined:structuredClone(initial);this.fail=false;}
  async get(key){assert.equal(key,"development-state-v1");return this.value===undefined?undefined:structuredClone(this.value);}
  async put(key,value){assert.equal(key,"development-state-v1");if(this.fail)throw Error("synthetic storage failure");this.value=structuredClone(value);}
}
function durableFixture(edits=false){
  let t=1000;
  const options={now:()=>t,requestTimeout:50};
  const reg={session_id:sid,session_end:7201000,deadline:3601000,allow_edits:edits,proof,catalog:edits?[...cat,{name:"multi_edit",inputSchema:{type:"object"}}]:cat};
  return {options,reg,at:v=>{t=v;}};
}
test("actual Relay reconstructs registration from durable storage after eviction",async()=>{
  const storage=new MemoryStorage(),r=new Relay({storage});
  const now=Date.now(),reg={session_id:sid,session_end:now+3600000,deadline:now+1800000,allow_edits:false,proof,catalog:cat};
  assert.equal((await call(r,"/development/register","100:1",reg)).status,200);
  const fresh=new Relay({storage});
  assert.equal((await call(fresh,"/development/poll","100:1",{session_id:sid})).status,200);
  assert.deepEqual(await (await call(fresh,"/development/catalog")).json(),{tools:cat});
  assert.equal((await call(fresh,"/development/poll","100:1",{session_id:"22345678-1234-4234-9234-123456789012"})).status,410);
});
test("durable handoff preserves retired runner fencing after reconstruction",async()=>{
  const {options,reg,at}=durableFixture(),storage=new MemoryStorage();
  let r=new DurableDevelopmentRelay(storage,options);
  assert.equal((await r.call("/development/register","100:1",reg)).status,200);
  at(1801000);
  assert.equal((await r.call("/development/poll","100:1",{session_id:sid})).status,200);
  assert.equal((await r.call("/development/register","200:1",{...reg,deadline:7201000})).status,200);
  r=new DurableDevelopmentRelay(storage,options);
  assert.equal((await r.call("/development/poll","100:1",{session_id:sid})).value.role,"retired");
  assert.equal((await r.call("/development/register","100:1",reg)).status,410);
  assert.equal((await r.call("/development/poll","200:1",{session_id:sid})).value.role,"active");
});
test("interrupted read request is never replayed; stale reply is rejected after restart",async()=>{
  const {options,reg}=durableFixture(),storage=new MemoryStorage();
  const old=new DurableDevelopmentRelay(storage,options);
  await old.call("/development/register","100:1",reg);
  const pending=old.call("/development/request",null,{name:"get_studio_state",arguments:{studio_id:"private-arg"}});
  const job=(await old.call("/development/poll","100:1",{session_id:sid})).value;
  assert.equal(job.action.name,"get_studio_state");
  assert.equal(storage.value.interrupted.delivered,true);
  assert.ok(!JSON.stringify(storage.value).includes("private-arg"));
  // Isolated snapshot simulates a new actor after the previous actor is gone.
  const restored=new DurableDevelopmentRelay(new MemoryStorage(storage.value),options);
  assert.equal((await restored.call("/development/poll","100:1",{session_id:sid})).value.request_id,null);
  assert.equal((await restored.call("/development/result","100:1",{request_id:job.request_id,generation:job.generation,result:{content:[]}})).status,409);
  assert.equal((await pending).status,504);
});
test("interrupted edit is quarantined until the bounded session ends",async()=>{
  const {options,reg,at}=durableFixture(true),storage=new MemoryStorage();
  const old=new DurableDevelopmentRelay(storage,options);
  await old.call("/development/register","100:1",reg);
  const pending=old.call("/development/request",null,{name:"multi_edit",arguments:{studio_id:"local"}});
  await old.call("/development/poll","100:1",{session_id:sid});
  const restarted=new DurableDevelopmentRelay(new MemoryStorage(storage.value),options);
  assert.equal((await restarted.call("/development/catalog",null)).status,503);
  assert.equal((await restarted.call("/development/request",null,{name:"multi_edit",arguments:{}})).status,409);
  assert.equal((await pending).status,504);
  at(7201000);
  assert.equal((await restarted.call("/development/catalog",null)).status,503);
});
test("storage failure before job delivery fails closed",async()=>{
  const {options,reg}=durableFixture(),storage=new MemoryStorage();
  const r=new DurableDevelopmentRelay(storage,options);
  await r.call("/development/register","100:1",reg);
  const pending=r.call("/development/request",null,{name:"get_studio_state",arguments:{}});
  // Wait for durable request admission; then simulate the delivery write failing.
  await r.tail;
  storage.fail=true;
  const failed=await r.call("/development/poll","100:1",{session_id:sid});
  assert.equal(failed.status,503);
  assert.equal(storage.value.interrupted.delivered,false);
  assert.equal((await pending).status,503);
});
