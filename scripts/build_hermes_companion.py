"""Build a fixed, disabled-by-default presentation candidate. Never install or connect."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / 'integrations/hermes-desktop'
UPSTREAM = '2237be355906fbe6065ce1815711eee52b2d646e'
MISSION = 'mission.public-learning.0001'
ERROR = 'Companion input failed validation; no installation or connection attempted.'


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError(ERROR)
        obj[k] = v
    return obj


def inspect_inputs(assessment: dict, raw: bytes) -> str:
    """Validate code-owned pins before packaging; not a privacy classifier or permit."""
    try:
        if assessment['upstream']['commit'] != UPSTREAM:
            raise ValueError(ERROR)
        if assessment['route'] != 'desktop_presentation_only':
            raise ValueError(ERROR)
        for key in ('default_enabled', 'runtime_enabled', 'network_enabled', 'persistence_enabled'):
            if assessment[key] is not False:
                raise ValueError(ERROR)
        if assessment['separate_records']['deployment_authorization'] is not None:
            raise ValueError(ERROR)
        w = assessment['workspace']
        if w['path'] != 'apps/learning-workspace/index.html' or w['mission_id'] != MISSION:
            raise ValueError(ERROR)
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 180_000 or sha(raw) != w['sha256']:
            raise ValueError(ERROR)
        text = raw.decode('utf-8')
        match = re.search(r'<script type="application/json" id="bundle">(.*?)</script>', text, re.S)
        data = json.loads(match.group(1), object_pairs_hook=_unique)
        mission = data['bundle']['mission']
        if (mission['mission_id'], mission['origin'], mission['data_classification']) != (
                MISSION, 'synthetic_fixture', 'public'):
            raise ValueError(ERROR)
        if "connect-src 'none'" not in text or "form-action 'none'" not in text:
            raise ValueError(ERROR)
        for tag in ('script', 'style'):
            body = re.search(r'<' + tag + r'>(.*?)</' + tag + r'>', text, re.S).group(1)
            digest = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
            if "'sha256-" + digest + "'" not in text:
                raise ValueError(ERROR)
        return text
    except (KeyError, TypeError, ValueError, AttributeError, UnicodeError):
        raise ValueError(ERROR) from None


def render_plugin(template: str, workspace: str) -> str:
    if template.count('__WORKSPACE_BASE64__') != 1:
        raise ValueError(ERROR)
    return template.replace('__WORKSPACE_BASE64__', base64.b64encode(workspace.encode()).decode())


def render_preview(workspace: str) -> str:
    """A plain browser frame test, explicitly not a running Hermes Desktop."""
    style = ('body{margin:0;background:#f4f3ee;color:#182f3c;font:15px/1.5 system-ui}'
             'header{padding:16px 24px;background:#102b3c;color:#fff}'
             'h1{font-size:23px;margin:3px 0}p{margin:5px 0}'
             '.tag{font-size:11px;letter-spacing:.12em;text-transform:uppercase}'
             'iframe{display:block;width:100%;height:calc(100vh - 155px);min-height:560px;border:0}'
             'footer{padding:9px 24px;font-size:12px}strong{font-weight:750}')
    style_hash = base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    script_hash = re.search(r"script-src ('sha256-[^']+')", workspace).group(1)
    child_style = re.search(r"style-src ('sha256-[^']+')", workspace).group(1)
    csp = (f"default-src 'none'; script-src {script_hash}; style-src 'sha256-{style_hash}' {child_style}; "
           "frame-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'")
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta http-equiv="Content-Security-Policy" content="{html.escape(csp, quote=True)}">'
            '<meta name="referrer" content="no-referrer"><title>SS-04A — Learning companion preview</title>'
            f'<style>{style}</style></head><body><header><div class="tag">Speed Sprint / SS-04A</div>'
            '<h1>Your workbench. A replaceable host.</h1>'
            '<p><strong>Browser integration preview — not Hermes Desktop.</strong> '
            'Fixed public/synthetic practice; no model, host account or runtime connection.</p></header>'
            '<iframe id="companion" title="Nurse AI OS learning companion" sandbox="allow-scripts allow-forms" '
            'referrerpolicy="no-referrer" allow="camera \'none\'; microphone \'none\'; geolocation \'none\'; '
            'clipboard-read \'none\'; clipboard-write \'none\'" '
            f'srcdoc="{html.escape(workspace, quote=True)}"></iframe>'
            '<footer>Presentation candidate only. Native-host review pending. '
            'Practice entries clear on reload; release and runtime gates remain closed.</footer></body></html>')


def build(output: Path) -> dict:
    assessment = json.loads((INTEGRATION / 'assessment.json').read_text(), object_pairs_hook=_unique)
    workspace = inspect_inputs(assessment, (ROOT / 'apps/learning-workspace/index.html').read_bytes())
    template = (INTEGRATION / 'plugin.template.js').read_text()
    plugin = render_plugin(template, workspace)
    preview = render_preview(workspace)
    # Explicit development output directory only. No HERMES_HOME discovery or installation.
    output.mkdir(parents=True, exist_ok=True)
    (output / 'plugin.js').write_text(plugin, encoding='utf-8')
    (output / 'preview.html').write_text(preview, encoding='utf-8')
    report = {'upstream_commit': UPSTREAM, 'workspace_sha256': sha(workspace.encode()),
              'plugin_sha256': sha(plugin.encode()), 'preview_sha256': sha(preview.encode()),
              'installed': False, 'native_host_tested': False, 'runtime_connected': False}
    (output / 'build-record.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='Explicit development output folder.')
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
