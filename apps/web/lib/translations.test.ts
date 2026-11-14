import test from 'node:test';
import assert from 'node:assert/strict';
import { defaults, evaluate } from './demo';
import { localizeResult, translate } from './translations';
import messages from './messages.tl.json';

test('Tagalog translations preserve every interpolation value', () => {
  const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map(match => match[1]).sort();
  for (const [english, tagalog] of Object.entries(messages)) {
    assert.deepEqual(placeholders(tagalog), placeholders(english), english);
    assert.ok(tagalog.trim());
  }
  assert.equal(translate('{crop} selling price', 'tl', { crop: 'Palay' }), 'Presyo ng bentahan ng Palay');
});

test('localization preserves constraints, money, identifiers and saved inputs', () => {
  const inputs = { ...defaults, simulation: true };
  const originalInputs = structuredClone(inputs);
  const results = evaluate(inputs);
  for (const result of results) {
    const originalResult = structuredClone(result);
    const localized = localizeResult(result, inputs, 'tl');
    assert.equal(localized.id, result.id);
    assert.equal(localized.feasibility, result.feasibility);
    assert.equal(localized.netIncome, result.netIncome);
    assert.equal(localized.releaseDate, result.releaseDate);
    assert.deepEqual(localized.checks.map(check => check.status), result.checks.map(check => check.status));
    assert.notEqual(localized.name, result.name);
    assert.ok(localized.checks.every((check, index) => check.detail !== result.checks[index].detail));
    assert.deepEqual(result, originalResult);
    assert.equal(localizeResult(result, inputs, 'en'), result);
  }
  assert.deepEqual(inputs, originalInputs);
});
