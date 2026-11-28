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
