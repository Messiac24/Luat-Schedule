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
    body: { classList: { toggle() {}, contains: () => false } },
    querySelectorAll: () => [],
    querySelector: () => null,
    getElementById: () => null,
    createElement: () => ({ appendChild() {} }),
    addEventListener() {},
  },
};

vm.runInNewContext(source, sandbox);

assert.equal(sandbox.formatClassFilterLabel('LH26B2DL'), 'LH26B2DL (VB2)');
assert.equal(sandbox.formatClassFilterLabel('LHK50DL'), 'LHK50DL (VLVH)');
assert.equal(sandbox.formatClassFilterLabel('LLT50DLCĐ'), 'LLT50DLCĐ (CĐ)');
assert.equal(sandbox.formatClassFilterLabel('LLT50DLTC'), 'LLT50DLTC (TC)');
assert.equal(sandbox.formatClassFilterLabel('UNKNOWN'), 'UNKNOWN');
assert.equal(sandbox.getStatusPriority('chưa học'), 0);
assert.equal(sandbox.getStatusPriority('Học bù'), 1);
assert.equal(sandbox.scheduleSortValueFromText('06/06/2026 (Thứ Bảy) - Sáng'), '2026-06-06');
assert.equal(sandbox.scheduleSortValueFromText('Không có lịch'), '');

const classNames = new Set(['subject-row', 'status-chưa-học', 'low-class-count', 'filtered-visible']);
const statusRow = {
  dataset: { lowClassCount: 'true' },
  classList: {
    add: (name) => classNames.add(name),
    remove: (name) => classNames.delete(name),
    forEach: (callback) => Array.from(classNames).forEach(callback),
    contains: (name) => classNames.has(name),
  },
};

sandbox.document.querySelector = (selector) => (
  selector === 'tr[data-id="LAW101"]' ? statusRow : null
);
sandbox.updateRowStatusClass('LAW101', 'Học bù');

assert.equal(classNames.has('status-chưa-học'), false);
assert.equal(classNames.has('status-học-bù'), true);
assert.equal(classNames.has('subject-row'), true);
assert.equal(classNames.has('low-class-count'), true);
assert.equal(classNames.has('filtered-visible'), true);

const rows = [
  {
    dataset: { viewIndex: '5', updatedAt: '', scheduleSort: '2026-06-13' },
    querySelector: (selector) => {
      if (selector === '.status-select') return { value: 'Chưa học' };
      if (selector === '.time-editor') return { value: '13/06/2026 (Thứ Bảy) - Sáng' };
      return null;
    },
  },
  {
    dataset: { viewIndex: '6', updatedAt: '', scheduleSort: '2026-06-06' },
    querySelector: (selector) => {
      if (selector === '.status-select') return { value: 'Chưa học' };
      if (selector === '.time-editor') return { value: '06/06/2026 (Thứ Bảy) - Sáng' };
      return null;
    },
  },
  {
    dataset: { viewIndex: '4', updatedAt: '2026-05-20T08:00:00+07:00', scheduleSort: '2026-06-01' },
    querySelector: (selector) => (selector === '.status-select' ? { value: 'Học bù' } : null),
  },
];

assert.deepEqual(rows.sort(sandbox.compareRowsBySchedule).map((row) => row.dataset.viewIndex), ['6', '5', '4']);

sandbox.document.getElementById = (id) => {
  const values = {
    'filter-class': 'lh26b2dl',
    'filter-semester': 'học kỳ i',
    'filter-subject': '',
    'filter-teacher': 'gv% a',
  };
  return { value: values[id] || '' };
};

assert.equal(
  sandbox.buildExportUrl(),
  '/api/export.xlsx?class=lh26b2dl&semester=h%E1%BB%8Dc+k%E1%BB%B3+i&teacher=gv%25+a',
);
