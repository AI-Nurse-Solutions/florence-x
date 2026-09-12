'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.join(__dirname,'../..');
const html=fs.readFileSync(path.join(root,'apps/learning-workspace/index.html'),'utf8');
const bundle=JSON.parse(html.match(/id="bundle">(.*?)<\/script>/s)[1]);
const context=vm.createContext({TextEncoder,console});
vm.runInContext(fs.readFileSync(path.join(root,'apps/learning-workspace/deliberation.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'apps/teaching-card/card.js'),'utf8'),context);
const engine=vm.runInContext('NAIODeliberation',context),cards=vm.runInContext('NAIOTeachingCard',context);
const view=bundle.deliberation,design={goal:'Explain one source limitation.',audience:'Personal learning',revision:0};
const clone=x=>JSON.parse(JSON.stringify(x));
let checks=0;const test=(name,f)=>{f();checks++;console.log('PASS '+name);};
const start=()=>engine.start(view,view.pack.cases[0].case_id);
const choice=(outcome='withhold')=>{
 let s=engine.apply(start(),view,'commit',{text:'PRIVATE_INITIAL_SENTINEL',uncertain:false});
 s=engine.apply(s,view,'reveal');
 s=engine.apply(s,view,'choose',{outcome,reason:'The evidence has scope limits.',alternative:'Examine the original source.',consequence:'Review takes time.',replacement:outcome==='revise'?'Use as a draft, not validated guidance.':null});
 return engine.apply(s,view,'reflect',{text:'PRIVATE_REFLECTION_SENTINEL'});
};
for(const outcome of ['accept','revise','reject','withhold'])test(outcome+' exact choice, disclosures and exclusions',()=>{
 const s=choice(outcome),before=JSON.stringify(s),c=cards.assemble(s,view,bundle,design,1),raw=JSON.stringify(c);
 assert.equal(c.provenance.choice.outcome,outcome);assert.equal(c.saved,false);assert.equal(c.submitted,false);
 assert.equal(c.independent_review,'pending');assert.equal(c.authority,'no_execution_permission');
 assert.equal(c.provenance.mission_sha256,s.mission_sha256);assert.equal(c.provenance.context_sha256,s.rounds[0].context_sha256);
 for(const p of c.provenance.sources){const original=bundle.evidence.passages.find(x=>x.passage_id===p.passage_id);assert.equal(p.quote,original.quote);assert.equal(p.revision,original.source.revision);assert.equal(p.support_status,'not_verified');}
 assert(!raw.includes('PRIVATE_INITIAL_SENTINEL'));assert(!raw.includes('PRIVATE_REFLECTION_SENTINEL'));
 assert(!raw.includes(s.rounds[0].case.proposal));assert.equal(JSON.stringify(s),before);
 assert.equal(c.catalog_state,'not_registered');assert.equal(c.template_version,'0.1.0');
 assert(c.markdown.includes('Independent review pending'));assert(Object.isFrozen(c));
});
test('no choice means no card',()=>assert.throws(()=>cards.assemble(start(),view,bundle,design,1)));
test('paused blocks',()=>assert.throws(()=>cards.assemble(engine.apply(choice(),view,'pause'),view,bundle,design,1)));
for(const reason of ['context_changed','evidence_view_changed'])test(reason+' blocks',()=>assert.throws(()=>cards.assemble(engine.apply(choice(),view,'invalidate',{reason}),view,bundle,design,1)));
for(const [field,value] of [['goal','Different goal'],['audience','Peer-learning draft'],['revision',1]])test(field+' changes binding',()=>{
 const s=choice();assert.notEqual(cards.binding(s,view,bundle,design),cards.binding(s,view,bundle,{...design,[field]:value}));
});
for(const [field,value] of [['goal',''],['goal','x'.repeat(281)],['audience','clinical'],['revision',-1],['revision','0']])test(field+' invalid value rejected',()=>assert.throws(()=>cards.assemble(choice(),view,bundle,{...design,[field]:value},1)));
for(const seq of [0,13,'1'])test('invalid draft sequence '+seq,()=>assert.throws(()=>cards.assemble(choice(),view,bundle,design,seq)));
for(const field of ['revision','locator','content_sha256'])test('changed source '+field+' cannot inherit binding',()=>{
 const b=clone(bundle);b.evidence.passages[0].source[field]=field==='content_sha256'?'a'.repeat(64):'different';
 assert.notEqual(cards.binding(choice(),view,bundle,design),cards.binding(choice(),view,b,design));
});
test('changed source text cannot inherit binding',()=>{
 const b=clone(bundle);b.evidence.passages[0].quote='Different passage';
 assert.notEqual(cards.binding(choice(),view,bundle,design),cards.binding(choice(),view,b,design));
});
for(const kind of ['missing','duplicate','nonpublic','mission','version'])test(kind+' evidence rejected',()=>{
 const b=clone(bundle);
 if(kind==='missing')b.evidence.passages.shift();if(kind==='duplicate')b.evidence.passages.push(clone(b.evidence.passages[0]));
 if(kind==='nonpublic')b.evidence.passages[0].source.data_classification='internal';if(kind==='mission')b.evidence.mission_id='other';if(kind==='version')b.evidence.version='1.0.0';
 assert.throws(()=>cards.assemble(choice(),view,b,design,1));
});
test('long wording rejected without changing original',()=>{
 const s=clone(choice());s.rounds[0].decision.reason='x'.repeat(1600);const before=JSON.stringify(s);
 assert.throws(()=>cards.assemble(s,view,bundle,design,1),/one_page_budget/);assert.equal(JSON.stringify(s),before);
});
test('raw HTML has inert Markdown escaping',()=>{
 const s=clone(choice());s.rounds[0].decision.reason='<img src=x onerror=alert(1)> [go](https://example.invalid)';
 const c=cards.assemble(s,view,bundle,design,1);assert(c.markdown.includes('\\<img'));assert(c.markdown.includes('\\[go\\]'));
});
test('design metadata cannot claim approval',()=>assert.throws(()=>cards.assemble(choice(),view,bundle,{...design,approved:true},1)));
test('no ambient browser, model or IO required',()=>{assert.equal(context.document,undefined);assert.equal(context.fetch,undefined);assert.equal(cards.assemble(choice(),view,bundle,design,1).persistence,'memory_only');});
console.log(JSON.stringify({passed:checks,scope:'pure_projection_tests_no_nurse_participants'}));
