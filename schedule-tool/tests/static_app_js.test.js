const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '..', 'static', 'js', 'app.js'),
  'utf8',
);

const sandbox = {
  console,
  setTimeout,
  URLSearchParams,
  window: { location: { href: '' } },
  document: {
    querySelectorAll: () => [],
    querySelector: () => null,
    getElementById: () => null,
    createElement: () => ({ appendChild() {} }),
  },
};

vm.runInNewContext(source, sandbox);

assert.equal(sandbox.formatClassFilterLabel('LH26B2DL'), 'LH26B2DL (VB2)');
assert.equal(sandbox.formatClassFilterLabel('LHK50DL'), 'LHK50DL (VLVH)');
assert.equal(sandbox.formatClassFilterLabel('LLT50DLCĐ'), 'LLT50DLCĐ (CĐ)');
assert.equal(sandbox.formatClassFilterLabel('LLT50DLTC'), 'LLT50DLTC (TC)');
assert.equal(sandbox.formatClassFilterLabel('UNKNOWN'), 'UNKNOWN');

sandbox.document.getElementById = (id) => {
  const values = {
    'filter-class': 'lh26b2dl',
    'filter-subject': '',
    'filter-teacher': 'gv% a',
  };
  return { value: values[id] || '' };
};

assert.equal(
  sandbox.buildExportUrl(),
  '/api/export.xlsx?class=lh26b2dl&teacher=gv%25+a',
);
