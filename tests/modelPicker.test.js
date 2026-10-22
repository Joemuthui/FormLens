// Run: node --test tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const MP = require('../src/modelPicker.js');

function model(id, inp, prompt, completion) {
  return {
    id, name: id,
    architecture: { input_modalities: inp, output_modalities: ['text'] },
    pricing: { prompt: String(prompt), completion: String(completion) },
  };
}

const CATALOGUE = [
  model('text/only', ['text'], 0.0000001, 0.0000004),
  model('vision/cheap', ['text', 'image'], 0.0000001, 0.0000005),
  model('vision/mid', ['text', 'image', 'file'], 0.000001, 0.000005),
  model('vision/pricey', ['text', 'image'], 0.000004, 0.00002),
  model('vision/cheap:batch', ['text', 'image'], 0.00000005, 0.00000025),
  model('vision/free:free', ['text', 'image'], 0, 0),
  model('openrouter/auto', ['text', 'image'], -1, -1),
];
const SHORT = [
  { id: 'vision/mid', reason: 'Benchmarked best', tested: true },
  { id: 'vision/pricey', reason: 'Strong', tested: false },
  { id: 'gone/model', reason: 'Not in catalogue', tested: true },
];

test('only image-capable, fixed-price, non-batch models are eligible', () => {
  const ids = MP.eligibleModels(CATALOGUE, { identifiable: false }).map(m => m.id);
  assert.deepEqual(ids.sort(), ['vision/cheap', 'vision/free:free', 'vision/mid', 'vision/pricey']);
});

test('free models are excluded when data is identifiable', () => {
  const ids = MP.eligibleModels(CATALOGUE, { identifiable: true }).map(m => m.id);
  assert.ok(!ids.includes('vision/free:free'));
});

test('cost estimate scales linearly with pages', () => {
  const m = CATALOGUE[2];
  const one = MP.estimateCost(m, 1);
  assert.ok(one > 0);
  assert.ok(Math.abs(MP.estimateCost(m, 2000) - one * 2000) < 1e-9);
  assert.equal(MP.estimateCost(CATALOGUE[6], 100), null);
});

test('balanced: tested shortlist first, missing shortlist entries ignored, max 3', () => {
  const recs = MP.recommend({ priority: 'balanced', identifiable: true, pages: 2000 }, CATALOGUE, SHORT);
  assert.equal(recs.length, 3);
  assert.equal(recs[0].id, 'vision/mid');
  assert.equal(recs[0].tested, true);
  assert.equal(recs[0].warning, null);
  assert.ok(!recs.some(r => r.id === 'gone/model'));
});

test('cost priority sorts by estimated cost', () => {
  const recs = MP.recommend({ priority: 'cost', identifiable: true, pages: 2000 }, CATALOGUE, SHORT);
  const costs = recs.map(r => r.estMonthlyCost);
  assert.deepEqual(costs, costs.slice().sort((a, b) => a - b));
  assert.equal(recs[0].id, 'vision/cheap');
});

test('untested models carry a warning for handwritten but not typed forms', () => {
  const hw = MP.recommend({ forms: 'handwritten', priority: 'cost' }, CATALOGUE, SHORT);
  assert.ok(hw.find(r => r.id === 'vision/cheap').warning);
  const typed = MP.recommend({ forms: 'typed', priority: 'cost' }, CATALOGUE, SHORT);
  assert.equal(typed.find(r => r.id === 'vision/cheap').warning, null);
});

test('privacy routing only when identifiable', () => {
  assert.deepEqual(MP.providerPrefs({ identifiable: true }), { zdr: true, data_collection: 'deny' });
  assert.equal(MP.providerPrefs({ identifiable: false }), undefined);
});

test('canSeeImages', () => {
  assert.equal(MP.canSeeImages(CATALOGUE[0]), false);
  assert.equal(MP.canSeeImages(CATALOGUE[1]), true);
  assert.equal(MP.canSeeImages({}), false);
});

test('formatCost', () => {
  assert.equal(MP.formatCost(null), '—');
  assert.equal(MP.formatCost(0.4), '<$1');
  assert.equal(MP.formatCost(23.6), '~$24');
  assert.equal(MP.formatCost(1234.4), '~$1,234');
});

test('imageStatus distinguishes ok / text-only / missing / unknown', () => {
  assert.equal(MP.imageStatus('vision/mid', CATALOGUE), 'ok');
  assert.equal(MP.imageStatus('text/only', CATALOGUE), 'text-only');
  assert.equal(MP.imageStatus('gone/model', CATALOGUE), 'missing');
  assert.equal(MP.imageStatus('vision/mid', null), 'unknown');
});
