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
