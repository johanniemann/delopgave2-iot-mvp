"""Execute browser state regressions against app.js without a live service."""
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
HARNESS = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { randomUUID } = require('node:crypto');
const listeners = new Map();
const nodes = new Map();
function element(id) {
  if (!nodes.has(id)) nodes.set(id, {
    id, innerHTML: '', textContent: '', dataset: {}, open: false,
    addEventListener() {}, setAttribute() {}, removeAttribute() {},
    showModal() { this.open = true; }, close() { this.open = false; },
  });
  return nodes.get(id);
}
const document = {
  body: { setAttribute() {}, removeAttribute() {} },
  getElementById: element,
  addEventListener(name, handler) {
    if (!listeners.has(name)) listeners.set(name, []);
    listeners.get(name).push(handler);
  },
};
const context = vm.createContext({
  document, window: { addEventListener() {}, scrollTo() {} },
  location: { hash: '' }, sessionStorage: { removeItem() {} },
  // Keep only automatic startup pending. Every test supplies its own API below.
  fetch: () => new Promise(() => {}),
  setTimeout: () => 1, clearTimeout() {}, crypto: { randomUUID },
  FormData: class {
    constructor(form) { this.fields = form.fields; }
    [Symbol.iterator]() { return Object.entries(this.fields)[Symbol.iterator](); }
  },
  renderCount: 0,
});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
vm.runInContext('render = () => { renderCount += 1; }; connection = () => {};', context);
const run = (code) => vm.runInContext(code, context);
function scenario(id) {
  return { id, title: `Window ${id}`, created_at: '2026-11-17T10:00:00Z',
    source: 'Synthetic test evidence', version: 1 };
}
const recent = Array.from({ length: 100 }, (_, i) => scenario(`recent-${i}`));
const older = {
  scenario: scenario('older-window'), case: { id: 'CASE-OLDER', status: 'Open' },
  outcomes: [],
};
const overview = { scenarios: recent, cases: [], active_scenario_id: recent[0].id };
const calls = [];
context.fixture = { older, overview, missing: false };
context.fetch = async (path, options = {}) => {
  calls.push({ path, options });
  let body;
  let status = 200;
  if (path === '/api/auth/me') body = {
    user: { role: 'technician', must_change_password: false }, csrf_token: randomUUID(),
  };
  else if (path === '/api/overview') body = overview;
  else if (path === '/api/scenarios/older-window') {
    if (context.fixture.missing) {
      status = 404; body = { error: { code: 'NOT_FOUND', message: 'Window not found' } };
    } else body = older;
  }
  else if (path === '/api/scenarios/recent-0') body = { scenario: recent[0] };
  else if (path === '/api/cases/CASE-OLDER/outcomes' && options.method === 'POST') {
    older.scenario.version += 1;
    older.case.status = 'Resolved';
    older.outcomes.push({ external_reference: 'synthetic-outcome' });
    body = { status: 'Resolved' };
  }
  else throw new Error(`Unexpected API request: ${options.method || 'GET'} ${path}`);
  return { ok: status < 400, status, json: async () => body };
};
"""


class BrowserStateTests(unittest.TestCase):
    def check_browser(self, javascript):
        self.assertIsNotNone(NODE, "Node.js is required for browser regression checks")
        result = subprocess.run(
            [NODE, "-e", HARNESS + "\n(async () => {\n" + javascript +
             "\n})().catch(error => { console.error(error); process.exitCode = 1; });",
             str(ROOT / "app/static/app.js")],
            text=True, capture_output=True, timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_initial_load_uses_active_scenario(self):
        self.check_browser("""
await run('load()');
assert.equal(run('S.detail.scenario.id'), 'recent-0');
assert.equal(run('renderCount'), 1);
""")

    def test_explicit_older_selection_is_loaded_beyond_recent_window(self):
        self.check_browser("""
await run('load("older-window")');
assert.equal(run('S.detail.scenario.id'), 'older-window');
assert.equal(run('S.data.scenarios.length'), 100);
assert.equal(calls.some(call => call.path === '/api/scenarios/recent-0'), false);
""")

    def test_refresh_keeps_selected_older_case(self):
        self.check_browser("""
run('S.detail = fixture.older; S.view = "case";');
await run('load()');
assert.equal(run('S.detail.case.id'), 'CASE-OLDER');
assert.equal(run('S.view'), 'case');
assert.equal(calls.at(-1).path, '/api/scenarios/older-window');
""")

    def test_missing_selected_window_does_not_silently_open_latest(self):
        self.check_browser("""
run('S.detail = fixture.older; fixture.missing = true;');
await assert.rejects(run('load()'), error => error.status === 404);
assert.equal(run('S.detail.case.id'), 'CASE-OLDER');
assert.equal(calls.some(call => call.path === '/api/scenarios/recent-0'), false);
""")

    def test_outcome_submission_refreshes_same_older_case(self):
        self.check_browser("""
run('S.detail = fixture.older; S.view = "case";');
const trigger = { innerHTML: 'Record outcome', dataset: {}, isConnected: true };
const form = {
  id: 'outcome-form', querySelector: () => trigger,
  fields: { result: 'success', external_reference: 'synthetic-outcome',
    evidence_reference: 'synthetic-evidence', note: 'Synthetic result' },
};
let prevented = false;
listeners.get('submit')[0]({ target: form, preventDefault() { prevented = true; } });
for (let i = 0; i < 30 && run('S.busy'); i++) await new Promise(setImmediate);
assert.equal(prevented, true);
assert.equal(run('S.busy'), false, 'Outcome task must finish');
assert.equal(run('S.detail.case.id'), 'CASE-OLDER');
assert.equal(run('S.detail.case.status'), 'Resolved');
assert.equal(run('S.detail.scenario.version'), 2);
assert.equal(run('S.detail.outcomes.length'), 1);
assert.equal(calls.at(-1).path, '/api/scenarios/older-window');
const write = calls.find(call => call.options.method === 'POST');
assert.equal(write.path, '/api/cases/CASE-OLDER/outcomes');
assert.equal(JSON.parse(write.options.body).expected_version, 1);
assert.equal(element('modal').open, false);
""")

    def test_picker_keeps_older_selection_and_labels_recent_window(self):
        self.check_browser("""
run('S.detail = fixture.older; S.data = fixture.overview;');
const html = run('picker()');
assert.match(html, /<option value="older-window" selected>/);
assert.match(html, /Selected older window/);
assert.match(html, /Latest 100/);
assert.equal((html.match(/<option /g) || []).length, 101);
run('S.detail = { scenario: fixture.overview.scenarios[0] };');
assert.equal((run('picker()').match(/<option /g) || []).length, 100,
  'A recent selection must not be duplicated');
""")

    def test_modal_header_treats_titles_and_descriptions_as_text(self):
        self.check_browser("""
context.titleText = '<img src=x onerror=alert(1)>';
context.descriptionText = 'A & B "quoted" <b>plain</b>';
const html = run('modalHeader(titleText, descriptionText)');
assert.ok(html.includes('<h2>&lt;img src=x onerror=alert(1)&gt;</h2>'));
assert.ok(html.includes('A &amp; B &quot;quoted&quot; &lt;b&gt;plain&lt;/b&gt;'));
assert.equal(html.includes('<img'), false);
assert.equal(html.includes('<b>plain</b>'), false);
""")

    def test_password_reset_escapes_saved_display_name(self):
        self.check_browser("""
context.account = { id: 'synthetic-user', version: 1,
  display_name: '<img src=x onerror=alert(1)> & <b>Tech</b>' };
run('resetPasswordModal(account)');
const html = element('modal-content').innerHTML;
assert.equal(element('modal').open, true);
assert.ok(html.includes('&lt;img src=x onerror=alert(1)&gt; &amp; &lt;b&gt;Tech&lt;/b&gt;'));
assert.equal(html.includes('<img'), false);
assert.equal(html.includes('<b>Tech</b>'), false);
assert.equal((html.match(/<form /g) || []).length, 1);
""")


if __name__ == "__main__":
    unittest.main()
