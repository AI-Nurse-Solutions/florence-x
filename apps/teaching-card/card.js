/* MD-01 pure projection. Prepared instructional design; never approval or persistence. */
const NAIOTeachingCard = (() => {
  const canonical = x => JSON.stringify(x, (_, v) => v && typeof v === 'object' && !Array.isArray(v)
    ? Object.keys(v).sort().reduce((o, k) => {o[k] = v[k]; return o;}, {}) : v);
  const copy = x => JSON.parse(JSON.stringify(x));
  const freeze = x => {if (x && typeof x === 'object') {Object.values(x).forEach(freeze); Object.freeze(x);} return x;};
  const fail = code => {throw new Error(code);};
  const audiences = ['Personal learning', 'Peer-learning draft', 'Educator review draft'];
  const titles = {accept:'Explain the basis for acceptance', revise:'Examine the revised wording',
    reject:'Learn from a rejected proposal', withhold:'Keep the unanswered question open'};
  const clean = (x, n) => typeof x === 'string' && x.trim() === x && x.length > 0 &&
    Array.from(x).length <= n && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u202a-\u202e\u2066-\u2069]/u.test(x);
  function inputs(session, view, bundle, design) {
    const s = NAIODeliberation.check(session, view), r = s.rounds.at(-1);
    if (s.paused || r.closed_reason !== 'none' || !r.revealed || !r.decision) fail('choice_not_current');
    const mission = bundle.bundle.mission, evidence = bundle.evidence;
    if (bundle.mission_sha256 !== s.mission_sha256 || mission.mission_id !== s.mission_id ||
        evidence.mission_id !== s.mission_id || evidence.mission_sha256 !== s.mission_sha256 ||
        view.pack.evidence_pack_id !== evidence.pack_id || view.pack.evidence_version !== evidence.version)
      fail('source_binding_invalid');
    if (!design || Object.keys(design).sort().join(',') !== 'audience,goal,revision' ||
        !clean(design.goal, 280) || !audiences.includes(design.audience) ||
        !Number.isSafeInteger(design.revision) || design.revision < 0) fail('design_invalid');
    if (new Set(evidence.passages.map(p => p.passage_id)).size !== evidence.passages.length)
      fail('source_binding_invalid');
    const sources = r.case.passage_ids.map(id => {
      const p = evidence.passages.find(x => x.passage_id === id);
      if (!p || p.source.data_classification !== 'public' || p.source.origin !== 'public_source' ||
          !/^[0-9a-f]{64}$/.test(p.source.content_sha256)) fail('source_binding_invalid');
      return {passage_id:id, title:p.title, source_id:p.source.source_id, revision:p.source.revision,
        excerpt_sha256:p.source.content_sha256, quote:p.quote, locator:p.source.locator,
        attribution:p.attribution, applicability:p.source.applicability, limitations:copy(p.limitations),
        rights_note:p.rights_note, inspection_scope:p.inspection_scope, support_status:'not_verified'};
    });
    const selected = {mission_id:s.mission_id, mission_sha256:s.mission_sha256, mission_goal:mission.goal,
      pack_sha256:s.pack_sha256, context_sha256:r.context_sha256, round:r.number,
      choice:copy(r.decision), sources, design:copy(design)};
    return freeze(selected);
  }
  function assemble(session, view, bundle, design, sequence) {
    const i = inputs(session, view, bundle, design), d = i.choice;
    if (!Number.isSafeInteger(sequence) || sequence < 1 || sequence > 12) fail('draft_limit');
    const words = [design.goal, d.reason, d.alternative, d.consequence, d.replacement || ''];
    if (words.some(x => !clean(x || '-', 2000))) fail('text_invalid');
    if (words.reduce((n, x) => n + Array.from(x).length, 0) > 1400) fail('one_page_budget_exceeded');
    const fields = [
      ['Learning objective · authored teaching design', design.goal],
      ['Knowledge · inspect the evidence', 'Read the linked passages. A source reference identifies context; it does not verify support for your conclusion.'],
      ['Judgment · your recorded choice', d.outcome.toUpperCase() + ' — ' + d.reason],
      ...(d.replacement ? [['Replacement · your unreviewed wording', d.replacement]] : []),
      ['Capability · alternative and consequence', 'Alternative: ' + d.alternative + '\nPossible consequence: ' + d.consequence],
      ['Contribution · teach-back prompt', 'Explain one source limitation and what evidence would change your choice. Seek independent review before relying on this draft.']
    ];
    const disclosure = 'Prepared AI-assisted exercise; fixed-template assembly, not live AI. Independent review pending. Learning effectiveness and competence not assessed. Unsaved; not submitted.';
    const plain = text => String(text).replace(/[\\`*_{}\[\]<>()#!|]/g, '\\$&');
    const markdown = '# ' + titles[d.outcome] + '\n\n' + fields.map(([k,v]) => '## ' + k + '\n' + plain(v)).join('\n\n') +
      '\n\n## Source context — support not verified\n' + i.sources.map(p => '- ' + plain(p.passage_id + ' · ' + p.source_id + ' · ' + p.revision)).join('\n') +
      '\n\n' + disclosure + '\n';
    return freeze({record_kind:'temporary_teaching_card', schema_version:'0.1.0',
      artifact_id:'tc.practice.round.' + i.round + '.draft.' + sequence, id_scope:'page_session_only',
      template_id:'teaching-card.practice', template_version:'0.1.0', catalog_state:'not_registered',
      compatible_payload_kind:'learning_guide', media_type:'text/markdown', title:titles[d.outcome],
      audience:design.audience, design_revision:design.revision, fields, disclosure, markdown,
      provenance:i, input_binding:canonical(i), actor_status:'not_authenticated',
      instructional_design:'authored_template_not_empirically_validated', independent_review:'pending',
      authority:'no_execution_permission', persistence:'memory_only', saved:false, submitted:false});
  }
  return Object.freeze({assemble, binding:(...args) => canonical(inputs(...args)), audiences:Object.freeze(audiences)});
})();
