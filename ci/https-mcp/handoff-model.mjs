// Credential-free reference state machine for a bounded CI development-session handoff.
// Not wired into the deployed Worker, and does not start or renew Actions jobs.
import {validResult} from "./worker.mjs";
export class HandoffModel {
  constructor({now=()=>Date.now(),sessionEnd,overlapMs=1800000,heartbeatMs=20000}={}) {
    if(!Number.isSafeInteger(sessionEnd)||sessionEnd<=now()||!Number.isSafeInteger(overlapMs)||overlapMs<1||!Number.isSafeInteger(heartbeatMs)||heartbeatMs<1) throw Error("invalid bounded session");
    this.now=now;this.sessionEnd=sessionEnd;this.overlapMs=overlapMs;this.heartbeatMs=heartbeatMs;
    this.active=null;this.standby=null;this.pending=null;this.generation=0;this.used=new Set();
  }
  fresh(r) { const t=this.now();return !!r&&t<this.sessionEnd&&t<r.deadline&&t-r.at<=this.heartbeatMs; }
  admit(id,deadline,proof) {
    const t=this.now();
    if(!/^\d+:\d+$/.test(id)||this.used.has(id)||!Number.isSafeInteger(deadline)||deadline<=t||deadline>this.sessionEnd||!validResult(proof)||!proof.verified) return false;
    if(this.active&&(this.standby||t<this.active.deadline-this.overlapMs))return false;
    const r={id,deadline,at:t};
    if(!this.active){this.active=r;this.generation++;}
    else this.standby=r;
    this.used.add(id);return true;
  }
  heartbeat(id) {
    const r=[this.active,this.standby].find(x=>x?.id===id);
    if(!r||this.now()>=r.deadline||this.now()>=this.sessionEnd)return false;
    r.at=this.now();return true;
  }
  promote() {
    // Never transfer in-flight work or let a stale/expired standby take ownership.
    if(this.pending||!this.fresh(this.standby))return false;
    this.active=this.standby;this.standby=null;this.generation++;return true;
  }
  begin(requestId) {
    if(this.pending||typeof requestId!=="string"||!requestId||!this.fresh(this.active))return null;
    this.pending={requestId,runner:this.active.id,generation:this.generation};return {...this.pending};
  }
  finish(id,requestId,generation) {
    const p=this.pending;
    if(!p||p.runner!==id||p.requestId!==requestId||p.generation!==generation)return false;
    this.pending=null;return true;
  }
  // Explicit timeout by caller. Never replay an ambiguous/mutating request.
  abandon(requestId,generation) {
    if(this.pending?.requestId!==requestId||this.pending?.generation!==generation)return false;
    this.pending=null;return true;
  }
}
