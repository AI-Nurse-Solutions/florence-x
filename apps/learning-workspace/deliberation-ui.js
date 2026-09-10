/* Local practice UI. Text-only rendering, explicit reveal, no persistence. */
(() => {
  const $=id=>document.getElementById(id);
  const node=(tag,text,cls='')=>{const e=document.createElement(tag);e.textContent=text;if(cls)e.className=cls;return e;};
  const forms=['initial-form','decision-form','reflection-form'];
  let session=null,view=null,valid=false;
  const readText=id=>$(id).value.trim()||null;
  const current=()=>session.rounds.at(-1);
  const fail=message=>{$('thinking-error').hidden=false;$('thinking-error').textContent=message;};
  const transition=(action,payload={})=>{
    try{session=NAIODeliberation.apply(session,view,action,payload);$('thinking-error').hidden=true;render();return true;}
    catch(_){fail('This step could not be recorded. Check the required fields, current round and pause state. Nothing was changed.');return false;}
  };
  function render(){
    const r=current(),stale=r.closed_reason!=='none',locked=session.paused||stale;
    $('round-label').textContent='Round '+r.number+' / 12 · '+(stale?'Context changed—new comparison required':r.reflection?'Reflection recorded in memory':r.decision?'Learning choice recorded in memory':r.revealed?'Compare and decide':r.initial?'Your interpretation is recorded—reveal when ready':'Begin with your own interpretation');
    $('thinking-stale').hidden=!stale;
    $('initial-snapshot').hidden=r.initial===null;
    $('initial-snapshot').textContent=r.initial?('Your initial view: '+(r.initial.text||'I am not ready to form an interpretation.')+(r.initial.uncertain?' · Uncertainty explicitly recorded.':'')):'';
    $('initial-fields').disabled=locked||r.initial!==null;
    $('compare-proposal').disabled=locked||r.initial===null||r.revealed;
    $('proposal-panel').hidden=!r.revealed;
    $('proposal-text').textContent=r.revealed?r.case.proposal:'';
    $('proposal-limitations').replaceChildren();
    if(r.revealed) r.case.limitations.forEach(t=>$('proposal-limitations').append(node('li',t)));
    $('proposal-links').replaceChildren();
    if(r.revealed) r.case.passage_ids.forEach(id=>{
      const b=node('button','Examine '+id,'secondary');b.type='button';b.disabled=session.paused;
      b.addEventListener('click',()=>{const d=$('passage-'+id);if(d){d.open=true;d.querySelector('summary').focus();d.scrollIntoView({block:'nearest'});}});
      $('proposal-links').append(b);
    });
    $('decision-panel').hidden=!r.revealed;
    $('decision-fields').disabled=locked||!r.revealed||r.decision!==null;
    $('decision-snapshot').hidden=r.decision===null;
    $('decision-snapshot').replaceChildren();
    if(r.decision){
      const d=r.decision;
      $('decision-snapshot').append(node('h3','Your learning choice: '+d.outcome),node('p','Reason: '+d.reason),node('p','Alternative: '+d.alternative),node('p','Consequence: '+d.consequence));
      if(d.replacement) $('decision-snapshot').append(node('p','Replacement wording: '+d.replacement));
      $('decision-snapshot').append(node('p','Practice only. No execution permission, source approval or portfolio save.','micro'));
    }
    $('reflection-panel').hidden=r.decision===null;
    $('reflection-fields').disabled=locked||r.decision===null||r.reflection!==null;
    $('reflection-snapshot').hidden=r.reflection===null;
    $('reflection-snapshot').textContent=r.reflection?'Your self-reflection: '+r.reflection:'';
    $('practice-case').disabled=session.paused;
    $('new-round').disabled=session.paused||session.rounds.length>=12||!valid;
    $('round-budget').textContent=session.rounds.length>=12?'Round limit reached. Inspect your record, then explicitly clear to start again.':'Earlier rounds are retained only for this page session.';
    const visible=JSON.parse(JSON.stringify(session));
    visible.rounds.forEach(x=>{if(!x.revealed)x.case.proposal='[Not revealed in this inspection view]';});
    $('thinking-json').textContent=JSON.stringify(visible,null,2);
    $('thinking-history').replaceChildren();
    session.rounds.slice(0,-1).forEach(old=>{
      const d=node('details','','round-history');
      d.append(node('summary','Round '+old.number+' · '+old.case.title+' · historical, not current'));
      d.append(node('p','Closed: '+old.closed_reason.replaceAll('_',' '),'micro'));
      d.append(node('p','Initial view: '+(old.initial?.text||(old.initial?.uncertain?'Uncertain.':'Not recorded.'))));
      if(old.revealed)d.append(node('p','Prepared proposal considered: '+old.case.proposal));
      if(old.decision){d.append(node('p','Learning choice: '+old.decision.outcome),node('p','Reason: '+old.decision.reason),node('p','Alternative: '+old.decision.alternative),node('p','Consequence: '+old.decision.consequence));if(old.decision.replacement)d.append(node('p','Replacement: '+old.decision.replacement));}
      if(old.reflection)d.append(node('p','Self-reflection: '+old.reflection));
      d.append(node('p','Context SHA-256: '+old.context_sha256,'micro'));
      $('thinking-history').append(d);
    });
  }
  function showCase(){
    const c=view.pack.cases.find(c=>c.case_id===$('practice-case').value);
    if(!c){valid=false;fail('Unknown exercise. No new comparison can begin.');return;}
    valid=true;$('practice-question').textContent=c.question;
    $('practice-observations').replaceChildren();c.observations.forEach(t=>$('practice-observations').append(node('li',t)));
  }
  function resetForms(){forms.forEach(id=>$(id).reset());$('replacement-group').hidden=true;$('replacement').required=false;}
  function newRound(){
    if(!valid)return;
    // Returning to baseline is explicit in this button's label and explanation.
    $('evidence-scenario').value='baseline';$('evidence-scenario').dispatchEvent(new Event('change'));
    if(transition('restart',{case_id:$('practice-case').value})){resetForms();render();$('initial-text').focus();}
  }
  try{
    const data=JSON.parse($('bundle').textContent);view=data.deliberation;
    if(!view||view.pack.mission_id!==data.bundle.mission.mission_id||view.pack.mission_sha256!==data.mission_sha256||view.pack.evidence_pack_id!==data.evidence.pack_id||view.pack.evidence_version!==data.evidence.version) throw new Error('binding');
    view.pack.cases.forEach(c=>{const o=node('option',c.title);o.value=c.case_id;$('practice-case').append(o);});
    showCase();session=NAIODeliberation.start(view,$('practice-case').value);render();
    $('initial-form').addEventListener('submit',e=>{e.preventDefault();if(transition('commit',{text:readText('initial-text'),uncertain:$('initial-uncertain').checked}))$('compare-proposal').focus();});
    $('compare-proposal').addEventListener('click',()=>{if(transition('reveal')){$('proposal-heading').focus();$('proposal-panel').scrollIntoView({block:'nearest'});}});
    $('decision-form').addEventListener('change',()=>{const outcome=document.querySelector('input[name="learning-choice"]:checked')?.value;$('replacement-group').hidden=outcome!=='revise';$('replacement').required=outcome==='revise';});
    $('decision-form').addEventListener('submit',e=>{
      e.preventDefault();const outcome=document.querySelector('input[name="learning-choice"]:checked')?.value;
      if(transition('choose',{outcome,reason:readText('decision-reason'),alternative:readText('decision-alternative'),consequence:readText('decision-consequence'),replacement:outcome==='revise'?readText('replacement'):null}))$('reflection-text').focus();
    });
    $('reflection-form').addEventListener('submit',e=>{e.preventDefault();transition('reflect',{text:readText('reflection-text')});});
    $('practice-case').addEventListener('change',()=>{showCase();transition('invalidate',{reason:'context_changed'});});
    $('evidence-scenario').addEventListener('change',()=>{transition('invalidate',{reason:'evidence_view_changed'});});
    $('new-round').addEventListener('click',newRound);
    $('pause').addEventListener('click',()=>{transition('pause');});
    $('clear-practice').addEventListener('click',()=>$('clear-dialog').showModal());
    $('cancel-clear').addEventListener('click',()=>$('clear-dialog').close());
    $('confirm-clear').addEventListener('click',()=>{
      const wasPaused=session.paused;
      $('clear-dialog').close();$('practice-case').value=view.pack.cases[0].case_id;
      $('evidence-scenario').value='baseline';$('evidence-scenario').dispatchEvent(new Event('change'));
      session=NAIODeliberation.start(view,$('practice-case').value);
      if(wasPaused)session=NAIODeliberation.apply(session,view,'pause');
      resetForms();showCase();render();$('thinking-notice').textContent='Practice entries cleared from this page session. No saved portfolio or external record exists.';
    });
    $('inspect-thinking').addEventListener('click',()=>{$('thinking-record').open=true;$('thinking-record').querySelector('summary').focus();});
  }catch(_){
    fail('This practice pack could not be opened. Nothing was recorded or connected.');
    document.querySelectorAll('#thinking-workbench input, #thinking-workbench textarea, #thinking-workbench select, #thinking-workbench button').forEach(e=>e.disabled=true);
  }
})();
