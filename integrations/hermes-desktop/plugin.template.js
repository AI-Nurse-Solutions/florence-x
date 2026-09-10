/* SS-04A presentation adapter. No host/session/tool/network/storage APIs.
 * This plugin itself is not sandboxed by Hermes. Keep disabled until reviewed.
 * The fixed child page is sandboxed; the parent remains a trusted dependency.
 */
import { jsx } from 'react/jsx-runtime';
const WORKSPACE = new TextDecoder().decode(
  Uint8Array.from(atob('__WORKSPACE_BASE64__'), c => c.charCodeAt(0))
);
export default {
  id: 'naio-learning-companion',
  name: 'Nurse AI OS — Learning Companion (review candidate)',
  description: 'Fixed public/synthetic practice. Temporary memory. No agent connection or execution authority.',
  defaultEnabled: false,
  register(ctx) {
    if (!ctx || typeof ctx.register !== 'function') {
      throw new Error('Unsupported desktop contribution context; nothing registered.');
    }
    ctx.register({
      id: 'learning-pane', area: 'panes', title: 'Nurse AI OS · Practice only',
      data: { placement: 'right', width: '760px' },
      render: () => jsx('iframe', {
        title: 'Nurse AI OS public learning practice — no live agent',
        sandbox: 'allow-scripts allow-forms',
        referrerPolicy: 'no-referrer',
        allow: "camera 'none'; microphone 'none'; geolocation 'none'; clipboard-read 'none'; clipboard-write 'none'",
        srcDoc: WORKSPACE,
        style: { width: '100%', height: '100%', minHeight: '520px', border: 0 }
      })
    });
  }
};
