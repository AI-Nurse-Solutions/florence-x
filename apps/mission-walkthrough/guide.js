/* Runs within the retained practice UI closure. No DOM state scraping, IO or authority. */
const guide = (() => {
  let currentSession = null, currentView = null, notes = [];
  const bundle = JSON.parse($('bundle').textContent);
  const binding = s => {
    const r = s.rounds.at(-1);
    return JSON.stringify([s.mission_sha256, s.pack_sha256, r.number, r.context_sha256, r.decision]);
  };
  const eligible = () => {
    if (!currentSession || currentSession.paused) return false;
    const r = currentSession.rounds.at(-1);
    return r.closed_reason === 'none' && r.revealed && r.decision !== null;
  };
  function show() {
    const last = notes.at(-1);
    const live = !!last && !!currentSession && eligible() && last.binding === binding(currentSession);
    $('compose-note').disabled = !eligible() || live || notes.length >= 12;
    $('note-card').hidden = !last;
    $('note-card').dataset.current = String(live);
    $('note-status').textContent = !currentSession ? 'Practice unavailable. Nothing assembled.' :
      currentSession.paused ? 'Paused. Note assembly is disabled; any displayed note is not a current completion claim.' :
      live ? 'This temporary note matches the current choice. It is not saved, approved or submitted.' :
      last ? 'Historical note: the current comparison changed. Review the new evidence and choice before assembling another note.' :
      eligible() ? 'Your choice is ready for explicit note assembly. No model will run.' : 'Record a learning choice first.';
    $('note-body').replaceChildren();
    if (last) {
      const n = last.note;
      const para = (label, text) => $('note-body').append(node('p', label + ': ' + text));
      para('Learning question', n.learning_question);
      para('Your choice', n.choice);
      if (n.revised_wording) para('Your revised wording', n.revised_wording);
      para('Your reason', n.reason); para('Alternative considered', n.alternative);
      para('Possible consequence', n.consequence);
      para('Use limitation', 'Learner-reported interpretation; not independently reviewed. This does not endorse the prepared proposal.');
      $('note-body').append(node('h3', 'Source context—not verified support'));
      const list = node('ul', '');
      n.sources.forEach(source => {
        const item = node('li', source.title + ' · ' + source.source_id + ' · ' + source.revision);
        const button = node('button', 'Inspect ' + source.passage_id, 'secondary'); button.type = 'button';
        button.addEventListener('click', () => {
          const target = $('passage-' + source.passage_id);
          if (target) { target.open = true; target.querySelector('summary').focus(); target.scrollIntoView({block:'nearest'}); }
        });
        item.append(button); list.append(item);
      });
      $('note-body').append(list);
      para('AI disclosure', n.ai_assistance);
      para('Storage', 'Temporary page memory only. No successful save receipt exists.');
    }
    $('note-json').textContent = notes.length ? JSON.stringify({
      record_kind: 'temporary_learning_review_notes', persistence: 'memory_only',
      authority: 'no_execution_permission', contribution_state: 'not_submitted',
      notes: notes.map((x, i) => ({...x.note, display_state: i === notes.length - 1 && live ? 'current_in_memory' : 'historical_in_memory'}))
    }, null, 2) : 'No note assembled.';
  }
  $('compose-note').addEventListener('click', () => {
    try {
      if (!eligible() || notes.length >= 12) return;
      NAIODeliberation.check(currentSession, currentView);
      const key = binding(currentSession);
      if (notes.at(-1)?.binding === key) return;
      const r = currentSession.rounds.at(-1), d = r.decision;
      const sources = r.case.passage_ids.map(id => {
        const source = bundle.evidence.passages.find(p => p.passage_id === id);
        if (!source) throw new Error('Unknown source');
        return {passage_id:id, title:source.title, source_id:source.source.source_id,
          revision:source.source.revision, excerpt_sha256:source.source.content_sha256,
          locator:source.source.locator, limitations:source.limitations,
          support_status:'not_verified'};
      });
      const note = {mission_id:currentSession.mission_id, mission_sha256:currentSession.mission_sha256,
        practice_pack_sha256:currentSession.pack_sha256, context_sha256:r.context_sha256,
        round:r.number, learning_question:r.case.question, choice:d.outcome, reason:d.reason,
        alternative:d.alternative, consequence:d.consequence, revised_wording:d.replacement,
        sources, content_review:'not_independently_reviewed', competence:'not_assessed',
        ai_assistance:'The practice proposal was a prepared AI-assisted fixture, not live inference. This note uses a fixed formatting template and your recorded choice.',
        excluded_fields:['initial_interpretation','reflection','SOUL','conversation_history'],
        persistence:'memory_only', saved:false, submitted:false};
      if (new TextEncoder().encode(JSON.stringify(note)).length > 32768) throw new Error('Size');
      notes.push({binding:key,note}); show();
      // Move focus only after explicit successful assembly, never on a view refresh.
      $('note-title').focus({preventScroll:true}); $('note-card').scrollIntoView({block:'nearest'});
    } catch (_) { $('note-status').textContent = 'Note assembly stopped. No new note, save or transmission occurred.'; }
  });
  return {update(s,v) { currentSession=s;currentView=v;show(); }, clear() { notes=[];show(); }};
})();
