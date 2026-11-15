import assert from 'node:assert/strict';
import { test } from 'node:test';
import { defaults, getPreviewComparison, validateInputs, windowDays } from './preview';
import { messages } from './messages';

test('the supplied HTML defaults retain the 197-day window and sample histories', () => {
  const result = getPreviewComparison(defaults, 'typical', 'even');
  assert.equal(result.mode, 'sample');
  assert.equal(result.days, 197);
  assert.equal(result.options[0].crop.id, 'mung');
  assert.deepEqual(result.options.find(option => option.crop.id === 'rice')?.history, [12, 44]);
  assert.equal(result.options.find(option => option.crop.id === 'rice')?.crop.days, 115);
});

test('standing water excludes the three alternatives, keeping the rice baseline', () => {
  const result = getPreviewComparison({ ...defaults, pond: 'yes' }, 'typical', 'even');
  assert.equal(result.options.filter(option => option.blocked === 'pond').length, 3);
  assert.equal(result.options.find(option => option.crop.id === 'rice')?.blocked, null);
});

test('calendar constraints apply before any sample score', () => {
  const result = getPreviewComparison({ ...defaults, next: '2026-12-01' }, 'dry', 'time');
  assert.ok(result.options.every(option => option.blocked === 'days' && option.index === null));
  const exact = getPreviewComparison({ ...defaults, next: '2027-01-19' }, 'typical', 'even');
  assert.equal(exact.options.find(option => option.crop.id === 'mung')?.blocked, null);
});

test('missing soil information stays missing, while unsure drainage requests confirmation', () => {
  const result = getPreviewComparison({ ...defaults, soil: '', pond: 'unsure' }, 'typical', 'even');
  assert.ok(result.options.every(option => option.missing.includes('ph') && option.missing.includes('tex')));
  assert.ok(result.options.filter(option => !option.crop.wet).every(option => option.checkDrainage));
});

test('season and water controls select the corresponding supplied history fixtures', () => {
  const result = getPreviewComparison({ ...defaults, water: 'irrig' }, 'nino', 'water');
  assert.deepEqual(result.options.find(option => option.crop.id === 'rice')?.history, [12, 14]);
  assert.equal(result.options.find(option => option.crop.id === 'rice')?.conditions.rain, .9);
});

test('invalid dates and pH never produce a comparison', () => {
  assert.equal(validateInputs({ ...defaults, harvest: '2026-02-30' }), 'dates');
  assert.equal(validateInputs({ ...defaults, next: defaults.harvest }), 'order');
  assert.equal(validateInputs({ ...defaults, ph: '11' }), 'ph');
  assert.equal(validateInputs({ ...defaults, ph: 'abc' }), 'ph');
  assert.equal(windowDays({ ...defaults, harvest: '' }), 0);
  assert.throws(() => getPreviewComparison({ ...defaults, ph: '11' }, 'typical', 'even'));
});

test('English and Tagalog catalogs have identical keys and preserve numeric placeholders', () => {
  function keys(value: object, prefix = ''): string[] {
    return Object.entries(value).flatMap(([key, item]) => typeof item === 'object' && item !== null ? keys(item, `${prefix}${key}.`) : [`${prefix}${key}`]).sort();
  }
  const en = messages('en'), tl = messages('tl');
  assert.deepEqual(keys(en), keys(tl));
  for (const key of ['win', 'hist', 'days', 'remaining', 'compareCount'] as const) {
    assert.deepEqual(en[key].match(/\{\w+\}/g), tl[key].match(/\{\w+\}/g));
  }
});
