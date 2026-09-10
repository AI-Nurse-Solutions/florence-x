/* Explicit synthetic JSX/host contract. This is not Electron/Hermes execution. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
(async () => {
  const source = fs.readFileSync(process.argv[2], 'utf8');
  const expected = fs.readFileSync('apps/learning-workspace/index.html', 'utf8');
  const context = vm.createContext({ TextDecoder, Uint8Array, atob });
  const imports = [];
  const jsx = new vm.SyntheticModule(['jsx'], function () {
    this.setExport('jsx', (tag, props) => ({ tag, props }));
  }, { context });
  const mod = new vm.SourceTextModule(source, { context });
  await mod.link(async name => {
    imports.push(name); assert.equal(name, 'react/jsx-runtime'); return jsx;
  });
  await mod.evaluate();
  const p = mod.namespace.default;
  let count = 0;
  function check(label, fn) { fn(); count++; console.log('PASS ' + label); }
  check('only the JSX import is used', () => assert.deepEqual(imports, ['react/jsx-runtime']));
  check('disabled by default', () => assert.equal(p.defaultEnabled, false));
  check('stable companion identity', () => assert.equal(p.id, 'naio-learning-companion'));
  check('missing contribution context refused', () => assert.throws(() => p.register(null)));
  const contributions = [];
  const ctx = new Proxy({}, { get(_, key) {
    assert.equal(key, 'register', 'No storage/RPC/OS/state access allowed by this test');
    return x => { contributions.push(x); return () => {}; };
  }});
  p.register(ctx);
  check('one pane and no backend registration', () => {
    assert.equal(contributions.length, 1); assert.equal(contributions[0].area, 'panes');
  });
  const frame = contributions[0].render();
  check('frame only', () => assert.equal(frame.tag, 'iframe'));
  check('only script and internal form-event sandbox permissions', () => assert.equal(frame.props.sandbox, 'allow-scripts allow-forms'));
  check('no referrer leakage', () => assert.equal(frame.props.referrerPolicy, 'no-referrer'));
  check('no live URL or parent messaging handler', () => {
    assert.equal(frame.props.src, undefined); assert.equal(frame.props.onLoad, undefined);
    assert.equal(frame.props.onMessage, undefined);
  });
  check('exact canonical workspace, not reauthored content', () => assert.equal(frame.props.srcDoc, expected));
  check('sensitive browser features denied', () => {
    for (const s of ['camera', 'microphone', 'geolocation', 'clipboard-read', 'clipboard-write']) {
      assert.ok(frame.props.allow.includes(s + " 'none'"));
    }
  });
  check('re-render keeps the same source without state reads', () => {
    assert.equal(contributions[0].render().props.srcDoc, expected);
  });
  const result = { checks: count, failed: 0, native_host: false,
    workspace_sha256: crypto.createHash('sha256').update(expected).digest('hex') };
  console.log(JSON.stringify(result));
})().catch(err => { console.error(err); process.exitCode = 1; });
