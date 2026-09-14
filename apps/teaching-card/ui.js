/* Inside the retained practice closure: consume validated state, never rendered JSON. */
const teaching = (() => {
  const bundle = JSON.parse($('bundle').textContent);
  let currentSession = null, currentView = null, designRevision = 0, drafts = [];
  // This predicate reads existing state; it retains no additional learner text.
  const leaveFields = Array.from(document.querySelectorAll(
    '#initial-form input, #initial-form textarea, #decision-form input, #decision-form textarea, ' +
    '#reflection-form textarea, #tc-goal, #tc-audience'));
  let leaveWarningActive = false;
  const hasUnsavedWork = () => drafts.length > 0 ||
    !!currentSession?.rounds.some(r => r.initial !== null || r.decision !== null || r.reflection !== null) ||
    leaveFields.some(field => {
      if (field.type === 'checkbox' || field.type === 'radio') return field.checked !== field.defaultChecked;
      if (field.tagName === 'SELECT') {
        const original = Array.from(field.options).find(option => option.defaultSelected) || field.options[0];
        return field.value !== original.value;
      }
      return field.value.trim() !== field.defaultValue.trim();
    });
  const warnBeforeLeaving = event => {
    if (!hasUnsavedWork()) return;
    event.preventDefault();
    event.returnValue = true; // Browser-controlled wording; legacy support, not a save.
  };
  function refreshLeaveWarning() {
    const needed = hasUnsavedWork();
    if (needed === leaveWarningActive) return;
    leaveWarningActive = needed;
    if (needed) window.addEventListener('beforeunload', warnBeforeLeaving);
    else window.removeEventListener('beforeunload', warnBeforeLeaving);
    $('tc-leave-status').textContent = needed
      ? 'Unsaved work is present. A browser warning is requested when you reload or leave. Nothing has been saved.'
      : 'No work is waiting to be kept. This page does not save your entries.';
  }
  leaveFields.forEach(field => {
    field.addEventListener('input', refreshLeaveWarning);
    field.addEventListener('change', refreshLeaveWarning);
  });
  const design = () => ({goal:$('tc-goal').value.trim(), audience:$('tc-audience').value, revision:designRevision});
  const binding = () => NAIOTeachingCard.binding(currentSession, currentView, bundle, design());
  const inspectSource = id => {
    const target = $('passage-' + id);
    if (target) {target.open = true; target.querySelector('summary').focus(); target.scrollIntoView({block:'nearest'});}
  };
  function fillCard(target, card, interactive) {
    target.replaceChildren();
    target.append(node('p', 'NURSE AI OS / PERSONAL LEARNING DRAFT', 'tc-eyebrow'));
    const heading = node('h3', card.title); if (interactive) {heading.id='tc-title';heading.tabIndex=-1;heading.setAttribute('aria-describedby','tc-status');}
    target.append(heading, node('p',card.audience + ' · ' + card.artifact_id,'tc-meta'));
    const grid=node('div','','tc-grid');
    card.fields.forEach(([label,text])=>{const section=node('section');section.append(node('h4',label),node('p',text));grid.append(section);});
    target.append(grid);
    const sources=node('div','','tc-sources');sources.append(node('h4','Source context · support not verified'));
    card.provenance.sources.forEach(p=>{
      const label=p.passage_id + ' · ' + p.source_id;
      if(interactive){const b=node('button',label,'secondary');b.type='button';b.addEventListener('click',()=>inspectSource(p.passage_id));sources.append(b);}
      else sources.append(node('span',label,'tc-source-label'));
    });
    sources.append(node('p','Exact source revisions, passages, limitations and attribution are in the companion below.','tc-meta'));
    target.append(sources,node('p',card.disclosure,'tc-disclosure'));
  }
  function show() {
    let key=null;try{key=binding();}catch(_){}
    const last=drafts.at(-1), live=!!last && key===last.input_binding;
    $('tc-compose').disabled=!key||live||drafts.length>=12;
    $('tc-goal').disabled=!!currentSession?.paused;$('tc-audience').disabled=!!currentSession?.paused;
    $('tc-card').hidden=!last;$('tc-card').dataset.current=String(live);
    $('tc-status').textContent=currentSession?.paused?'Paused. Card assembly is disabled; drafts remain unsaved.':
      live?'Current temporary teaching card. One-page target fits; not saved, approved or submitted.':
      last?'Historical teaching card. Context or design changed; assemble a new draft only after a current learning choice.':
      key?'Your recorded choice is ready. Assemble explicitly; no AI model will run.':'Record a current learning choice first. Nothing is saved.';
    $('tc-card').replaceChildren();$('tc-companion-body').replaceChildren();
    if(last){
      fillCard($('tc-card'),last,true);
      last.provenance.sources.forEach(p=>{
        const section=node('section');section.append(node('h4',p.title),node('p',p.attribution),node('blockquote',p.quote),
          node('p','Revision: '+p.revision),node('p','Location: '+p.locator),node('p','Applicability: '+p.applicability),
          node('p','Inspection: '+p.inspection_scope),node('p','Reuse note: '+p.rights_note));
        p.limitations.forEach(t=>section.append(node('p','Limit: '+t)));$('tc-companion-body').append(section);
      });
    }
    $('tc-json').textContent=drafts.length?JSON.stringify({persistence:'memory_only',authority:'no_execution_permission',
      drafts:drafts.map((x,i)=>({...x,display_state:i===drafts.length-1&&live?'current_in_memory':'historical_in_memory'}))},null,2):'No teaching card assembled.';
    refreshLeaveWarning();
  }
  $('tc-compose').addEventListener('click',()=>{
    try{
      const key=binding();if(drafts.at(-1)?.input_binding===key||drafts.length>=12)return;
      const candidate=NAIOTeachingCard.assemble(currentSession,currentView,bundle,design(),drafts.length+1);
      // Measure the same controls/typography at the explicit one-page target. No clipping or shrinking.
      fillCard($('tc-measure'),candidate,true);
      const heading=$('tc-measure').querySelector('h3');heading.removeAttribute('id');heading.removeAttribute('aria-describedby');
      const rect=$('tc-measure').getBoundingClientRect();
      const fits=rect.height<=960&&$('tc-measure').scrollWidth<=720;
      $('tc-measure').replaceChildren();
      if(!fits)throw new Error('one_page_budget_exceeded');
      drafts.push(candidate);show();$('tc-title').focus({preventScroll:true});$('tc-card').scrollIntoView({block:'nearest'});
    }catch(error){
      $('tc-measure').replaceChildren();
      $('tc-status').textContent=error.message==='one_page_budget_exceeded'
        ?'Not assembled: this wording exceeds the readable one-page target. Shorten the objective or start a new comparison with more concise wording. No content was clipped or saved.'
        :'Card assembly stopped. Check the current choice, scope and draft limit. No card was saved or transmitted.';
    }
  });
  for(const id of ['tc-goal','tc-audience'])$(id).addEventListener(id==='tc-goal'?'input':'change',()=>{designRevision+=1;show();});
  return {update(s,v){currentSession=s;currentView=v;show();},clear(){drafts=[];designRevision=0;$('tc-goal').value=$('tc-goal').defaultValue;$('tc-audience').selectedIndex=0;show();}};
})();
