import test from 'node:test';
import assert from 'node:assert/strict';
import { defaults, evaluate, validateInputs } from './demo';
import sample from './power-sample.json';

test('archived NASA cards match the complete daily source sample', () => {
  const temperatures = Object.values(sample.raw.properties.parameter.T2M_MAX);
  const rainfall = Object.values(sample.raw.properties.parameter.PRECTOTCORR);
  assert.equal(temperatures.length, 30);
  assert.equal(rainfall.length, 30);
  assert.equal(sample.raw.parameters.T2M_MAX.units, 'C');
  assert.equal(sample.raw.parameters.PRECTOTCORR.units, 'mm/day');
  assert.ok([...temperatures, ...rainfall].every(n => Number.isFinite(n) && n !== sample.raw.header.fill_value));
  assert.equal(sample.meanDailyMaximumC, Number((temperatures.reduce((a,b) => a+b,0)/30).toFixed(1)));
  assert.equal(sample.precipitationTotalMm, Number(rainfall.reduce((a,b) => a+b,0).toFixed(1)));
});

test('hard water constraints exclude rice regardless of income priority', () => {
  const [rice] = evaluate({ ...defaults, priority: 'income', simulation: true });
  assert.equal(rice.feasibility, 'infeasible');
  assert.ok(rice.checks.some(c => c.label === 'Water availability' && c.status === 'fail'));
});
test('missing drainage and buyer information stays unknown', () => {
  assert.equal(evaluate(defaults)[1].feasibility, 'unknown');
});
test('a fully supported demo input can pass without claiming agronomic validity', () => {
  const results = evaluate({ ...defaults, drainage: 'well_drained', buyer: 'available' });
  assert.equal(results[1].feasibility, 'feasible');
  assert.equal(results[1].estimateBasis, 'unavailable');
  assert.equal(results[1].netIncome, null);
});
test('deadline and budget remain hard constraints', () => {
  const r = evaluate({ ...defaults, riceDeadline: '2027-02-01', budget: 5000, drainage: 'well_drained', buyer: 'available' })[1];
  assert.equal(r.feasibility, 'infeasible');
  assert.equal(r.checks.filter(c => c.status === 'fail').length, 2);
});
test('price changes affect money, preserve biological fixtures, and do not double count upfront costs', () => {
  const a = evaluate({ ...defaults, simulation: true })[1];
  const b = evaluate({ ...defaults, simulation: true, mungbeanPrice: 70 })[1];
  assert.equal(a.yieldKg, b.yieldKg);
  assert.equal(a.releaseDate, b.releaseDate);
  assert.equal(b.netIncome! - a.netIncome!, 4500);
  assert.equal(a.netIncome, a.revenue! - a.totalCost);
});
test('invalid dates and nonfinite values are rejected', () => {
  assert.ok(validateInputs({ ...defaults, area: NaN }));
  assert.ok(validateInputs({ ...defaults, plantingDate: '2027-02-30' }));
  assert.ok(validateInputs({ ...defaults, riceDeadline: defaults.plantingDate }));
});
