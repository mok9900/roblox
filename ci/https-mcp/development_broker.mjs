// Staged bounded development relay. Requires authenticated runner identity
// from the existing Worker; no public path to this class.
const MAX_SESSION=24*60*60*1000, OVERLAP=30*60*1000, FRESH=20000;
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const RUN=/^\d+:\d+$/;
const READ=new Set(["list_roblox_studios","get_studio_state","search_game_tree","inspect_instance","script_search","script_read","script_grep","get_console_output","screen_capture","list_skills","skill"]);
const EDIT=new Set(["multi_edit","save_place","start_stop_play","user_mouse_input","user_keyboard_input","character_navigation","generate_procedural_model"]);
const isObject=v=>v&&typeof v==="object"&&!Array.isArray(v);
const bytes=v=>new TextEncoder().encode(JSON.stringify(v)).length;
const reply=(v,status=200)=>({status,value:v});
const error=(s,status=409)=>reply({error:s},status);
function verified(v){return isObject(v)&&v.verified===true&&v.matching_local_fixtures===1&&v.source==="official_studio_mcp";}
function validCatalog(c,edits){
  if(!Array.isArray(c)||c.length>READ.size+EDIT.size)return false;
  const seen=new Set();
  for(const t of c){
    if(!isObject(t)||typeof t.name!=="string"||seen.has(t.name)||!(READ.has(t.name)||(edits&&EDIT.has(t.name)))||!isObject(t.inputSchema))return false;
    seen.add(t.name);
  }
  return seen.has("list_roblox_studios")&&bytes(c)<=60000;
}
export class DevelopmentBroker {
  constructor({now=()=>Date.now(),makeId=()=>crypto.randomUUID(),requestTimeout=60000}={}){
    this.now=now;this.makeId=makeId;this.requestTimeout=requestTimeout;
    this.session=null;this.active=null;this.standby=null;this.pending=null;
    this.generation=0;this.used=new Set();
  }
  fresh(r){return !!r&&this.now()<r.deadline&&this.now()-r.at<=FRESH&&this.now()<this.session.end;}
  promote(){
    if(this.pending||!this.fresh(this.standby))return false;
    this.active=this.standby;this.standby=null;this.generation++;return true;
  }
  clean(){
    if(this.standby&&this.now()>=this.standby.deadline)this.standby=null;
    if(this.session&&this.now()>=this.session.end&&!this.pending){
      this.session=null;this.active=null;this.standby=null;this.used.clear();
    }
  }
  register(id,b){
    this.clean();const now=this.now();
    if(!RUN.test(id)||!isObject(b)||!UUID.test(b.session_id)||!Number.isSafeInteger(b.session_end)||b.session_end<=now||b.session_end>now+MAX_SESSION||!Number.isSafeInteger(b.deadline)||b.deadline<=now||b.deadline>b.session_end||typeof b.allow_edits!=="boolean"||!verified(b.proof)||!validCatalog(b.catalog,b.allow_edits))return error("Invalid registration",400);
    if(this.session&&(this.session.id!==b.session_id||this.session.end!==b.session_end||this.session.edits!==b.allow_edits))return error("Another bounded session is active");
    if(!this.session){
      this.session={id:b.session_id,end:b.session_end,edits:b.allow_edits};
    }
    const existing=[this.active,this.standby].find(x=>x?.id===id);
    if(existing){
      if(existing.deadline!==b.deadline)return error("Deadline changed");
      existing.at=now;existing.catalog=b.catalog;return reply({registered:true});
    }
    if(this.used.has(id))return error("Runner retired",410);
    if(this.active&&this.standby)return error("Standby occupied");
    if(this.active&&now<this.active.deadline-OVERLAP&&this.fresh(this.active))return error("Outside handoff window");
    const candidate={id,deadline:b.deadline,at:now,catalog:b.catalog};
    this.used.add(id);
    if(!this.active){this.active=candidate;this.generation++;}
    else {this.standby=candidate;this.promote();}
    return reply({registered:true});
  }
  poll(id,b){
    this.clean();
    if(!this.session||b?.session_id!==this.session.id)return error("Session unavailable",410);
    const r=[this.active,this.standby].find(x=>x?.id===id);
    if(!r)return reply({role:"retired",request_id:null});
    if(this.now()>=r.deadline||this.now()>=this.session.end)return reply({role:"retired",request_id:null});
    r.at=this.now();
    if(!this.pending)this.promote();
    if(this.active?.id!==id)return reply({role:this.standby?.id===id?"standby":"retired",request_id:null});
    const p=this.pending;
    if(p&&p.runner===id&&!p.delivered){p.delivered=true;return reply({role:"active",request_id:p.id,generation:p.generation,action:p.action});}
    return reply({role:"active",request_id:null});
  }
  catalog(){
    this.clean();if(!this.pending)this.promote();
    return this.fresh(this.active)?reply({tools:this.active.catalog}):error("Development runner unavailable",503);
  }
  request(action){
    this.clean();if(!this.pending)this.promote();
    if(!this.fresh(this.active))return error("Development runner unavailable",503);
    if(this.pending)return error("Busy",409);
    if(!isObject(action)||!isObject(action.arguments)||typeof action.name!=="string"||bytes(action)>60000)return error("Invalid action",400);
    if(action.name!=="verify_ci_studio"&&!this.active.catalog.some(t=>t.name===action.name))return error("Tool denied",403);
    const id=this.makeId(),runner=this.active.id,generation=this.generation;
    return new Promise(resolve=>{
      const timer=setTimeout(()=>{
        if(this.pending?.id===id)this.pending=null;
        resolve(error("Request timeout; outcome unknown",504));
      },this.requestTimeout);
      this.pending={id,runner,generation,action,delivered:false,finish:(v)=>{
        clearTimeout(timer);this.pending=null;resolve(v);
      }};
    });
  }
  result(id,b){
    const p=this.pending;
    if(!p||!p.delivered||p.runner!==id||b?.request_id!==p.id||b.generation!==p.generation)return error("Stale request");
    if(!isObject(b.result)||bytes(b.result)>60000)return error("Invalid result",400);
    p.finish(reply({result:b.result}));this.promote();return reply({accepted:true});
  }
}
