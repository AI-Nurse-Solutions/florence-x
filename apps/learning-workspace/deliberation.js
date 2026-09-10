/* SS-03 pure in-memory transitions. No IO. Learning choices are not approvals. */
'use strict';
const NAIODeliberation = (() => {
  const outcomes=['accept','revise','reject','withhold'];
  const reasons=['none','restarted','context_changed','evidence_view_changed'];
  const error=()=>new Error('Invalid or out-of-order practice request; nothing changed.');
  const clone=x=>JSON.parse(JSON.stringify(x));
  const canonical=x=>JSON.stringify(x, function(k,v){return v && typeof v==='object' && !Array.isArray(v)?Object.keys(v).sort().reduce((o,key)=>{o[key]=v[key];return o;},{}):v;});
  const equal=(a,b)=>canonical(a)===canonical(b);
  const keys=(x,want)=>x && typeof x==='object' && !Array.isArray(x) && equal(Object.keys(x).sort(),want.slice().sort());
  const text=x=>typeof x==='string' && x.trim()===x && Array.from(x).length>0 && Array.from(x).length<=2000;
  const digest=x=>typeof x==='string' && /^[0-9a-f]{64}$/.test(x);
  const freeze=x=>{if(x && typeof x==='object'){Object.values(x).forEach(freeze);Object.freeze(x);}return x;};
  function fixture(v){
    if(!v || !v.pack || !digest(v.pack_sha256) || !v.case_digests) throw error();
    const p=v.pack;
    if(p.schema_version!=='0.1.0'||p.data_classification!=='public'||!digest(p.mission_sha256)||p.cases.length!==3||new Set(p.cases.map(c=>c.case_id)).size!==3) throw error();
    for(const c of p.cases) if(c.origin!=='synthetic_fixture'||c.proposal_disclosure!=='prepared_ai_assisted_fixture_not_live_model'||!text(c.proposal)||!digest(v.case_digests[c.case_id])) throw error();
    return p;
  }
  function check(s,v){
    const p=fixture(v);
    if(!keys(s,['schema_version','session_id','mission_id','mission_sha256','pack_sha256','scope','persistence','actor_status','authority','paused','rounds'])) throw error();
    if(s.schema_version!=='0.1.0'||s.session_id!=='practice.local.session'||s.mission_id!==p.mission_id||s.mission_sha256!==p.mission_sha256||s.pack_sha256!==v.pack_sha256||s.scope!=='nonclinical_practice'||s.persistence!=='memory_only'||s.actor_status!=='not_authenticated'||s.authority!=='no_execution_permission'||typeof s.paused!=='boolean'||!Array.isArray(s.rounds)||s.rounds.length<1||s.rounds.length>12) throw error();
    if(new TextEncoder().encode(JSON.stringify(s)).length>262144) throw error();
    s.rounds.forEach((r,i)=>{
      if(!keys(r,['number','case','context_sha256','initial','revealed','decision','reflection','closed_reason'])||r.number!==i+1||typeof r.revealed!=='boolean'||!reasons.includes(r.closed_reason)) throw error();
      const c=p.cases.find(c=>c.case_id===r.case?.case_id);
      if(!c||!equal(c,r.case)||r.context_sha256!==v.case_digests[c.case_id]||(i<s.rounds.length-1&&r.closed_reason==='none')) throw error();
      if(r.initial!==null){
        if(!keys(r.initial,['text','uncertain'])||typeof r.initial.uncertain!=='boolean'||(r.initial.text!==null&&!text(r.initial.text))||(r.initial.text===null&&!r.initial.uncertain)) throw error();
      }
      if(r.revealed&&r.initial===null) throw error();
      if(r.decision!==null){
        const d=r.decision;
        if(!r.revealed||!keys(d,['outcome','reason','alternative','consequence','replacement'])||!outcomes.includes(d.outcome)||!text(d.reason)||!text(d.alternative)||!text(d.consequence)) throw error();
        if(d.outcome==='revise'?!text(d.replacement):d.replacement!==null) throw error();
      }
      if(r.reflection!==null&&(!text(r.reflection)||r.decision===null)) throw error();
    });
    return freeze(clone(s));
  }
  const freshRound=(v,id,n)=>{
    const c=fixture(v).cases.find(c=>c.case_id===id);if(!c) throw error();
    return {number:n,case:clone(c),context_sha256:v.case_digests[id],initial:null,revealed:false,decision:null,reflection:null,closed_reason:'none'};
  };
  function start(v,id){const p=fixture(v);return check({schema_version:'0.1.0',session_id:'practice.local.session',mission_id:p.mission_id,mission_sha256:p.mission_sha256,pack_sha256:v.pack_sha256,scope:'nonclinical_practice',persistence:'memory_only',actor_status:'not_authenticated',authority:'no_execution_permission',paused:false,rounds:[freshRound(v,id,1)]},v);}
  function apply(s,v,action,payload={}){
    const d=clone(check(s,v)),r=d.rounds.at(-1);
    if(!payload||typeof payload!=='object'||Array.isArray(payload)) throw error();
    if(action==='pause'){
      if(!keys(payload,[])) throw error();d.paused=!d.paused;
    }else if(action==='invalidate'){
      if(!keys(payload,['reason'])||!['context_changed','evidence_view_changed'].includes(payload.reason)) throw error();
      if(r.closed_reason==='none') r.closed_reason=payload.reason;
    }else{
      if(d.paused) throw error();
      if(action==='restart'){
        if(!keys(payload,['case_id'])||d.rounds.length>=12) throw error();
        if(r.closed_reason==='none') r.closed_reason='restarted';
        d.rounds.push(freshRound(v,payload.case_id,d.rounds.length+1));
      }else{
        if(r.closed_reason!=='none') throw error();
        if(action==='commit'&&r.initial===null){
          if(!keys(payload,['text','uncertain'])) throw error();
          r.initial=clone(payload);
        }else if(action==='reveal'&&r.initial!==null&&!r.revealed&&keys(payload,[])) r.revealed=true;
        else if(action==='choose'&&r.revealed&&r.decision===null) r.decision=clone(payload);
        else if(action==='reflect'&&r.decision!==null&&r.reflection===null&&keys(payload,['text'])&&text(payload.text)) r.reflection=payload.text;
        else throw error();
      }
    }
    return check(d,v);
  }
  const safe=fn=>(...args)=>{try{return fn(...args);}catch(_){throw error();}};
  return Object.freeze({start:safe(start),apply:safe(apply),check:safe(check)});
})();
if(typeof module!=='undefined'&&module.exports) module.exports=NAIODeliberation;
