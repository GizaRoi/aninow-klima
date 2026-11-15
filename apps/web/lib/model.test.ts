import assert from 'node:assert/strict';
import { test } from 'node:test';
import catalogData from '../../../tests/fixtures/catalog.json';
import comparisonData from '../../../tests/fixtures/comparison.json';
import expandedCatalog from '../../../tests/fixtures/expanded-catalog.json';
import expandedComparison from '../../../tests/fixtures/expanded-comparison.json';
import fallowComparison from '../../../tests/fixtures/expanded-fallow.json';
import { compare, cropFit, cropOptions, defaults, getCatalog, ModelError, parseCatalog, parseComparison, toModelInputs, validateInputs } from './model';
import { messages } from './messages';

test('captured Render response uses real crops, denominators, nulls and exclusions', () => {
  const catalog = parseCatalog(catalogData), comparison = parseComparison(comparisonData);
  const options = cropOptions(comparison, catalog, 'balanced');
  assert.equal(options.length, 10);
  assert.equal(options[0].crop.id, 'mungbean');
  assert.equal(options[0].result.counts.balanced.all.short.of, 41);
  assert.equal(options.find(o => o.crop.id === 'rice')!.result.scored_days.short, 106);
  assert.deepEqual(options.find(o => o.crop.id === 'potato')!.excluded, ['warmer_than_guide_range']);
  assert.equal(comparison.results.fields.irrigation.crops.rice.median_scores.short.water, null);
  assert.deepEqual(cropOptions(comparison, catalog, 'finishing_early').filter(o => !o.excluded.length).map(o => o.crop.id), comparison.results.fields.rain.rankings.finishing_early);
});

test('blank measured overrides stay null and explicit overrides retain their units', () => {
  assert.deepEqual(toModelInputs(defaults, 'balanced'), { ...comparisonData.inputs, prep_days: 0, picking_days: 0 });
  const payload = toModelInputs({ ...defaults, soil_ph: '6.3', soil_texture: 'medium', turnaround_days: '14', pass_mark: '0' }, 'saving_water');
  assert.equal(payload.soil_ph, 6.3);
  assert.equal(payload.soil_texture, 'medium');
  assert.equal(payload.turnaround_days, 14);
  assert.equal(payload.pass_mark, 0);
});

test('API date and numeric constraints are checked before sending', () => {
  for (const [overrides, expected] of [
    [{ harvest: '2026-02-30' }, 'dates'], [{ harvest: '2028-02-29' }, 'leap'],
    [{ next_planting: '2028-05-31' }, 'annual'], [{ next_planting: defaults.harvest }, 'order'],
    [{ soil_ph: 'Infinity' }, 'ph'], [{ turnaround_days: '1.5' }, 'preparation'],
    [{ turnaround_days: '' }, 'preparation'], [{ pass_mark: '' }, 'passMark'], [{ pass_mark: '1.1' }, 'passMark'],
  ] as const) assert.equal(validateInputs({ ...defaults, ...overrides }), expected);
});

test('sample or incomplete responses cannot be displayed as a successful model run', () => {
  assert.throws(() => parseComparison({ ...comparisonData, mode: 'sample' }), ModelError);
  const broken = structuredClone(comparisonData);
  delete (broken.results.fields.rain.crops.mungbean.counts.balanced as Record<string, unknown>).dry;
  assert.throws(() => parseComparison(broken), ModelError);
  assert.throws(() => parseCatalog({ ...catalogData, contract_version: 'v2' }), ModelError);
});

test('client sends JSON, handles service errors, and never substitutes fixtures', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async (url, init) => {
    assert.match(String(url), /\/api\/v1\/compare$/);
    assert.equal(init?.method, 'POST');
    assert.deepEqual(JSON.parse(String(init?.body)), { ...comparisonData.inputs, prep_days: 0, picking_days: 0 });
    return Response.json(comparisonData);
  };
  assert.equal((await compare(defaults, 'balanced')).mode, 'rules_model');
  for (const [status, kind] of [[422, 'validation'], [503, 'busy'], [504, 'timeout']] as const) {
    globalThis.fetch = async () => Response.json({ error: { field_errors: { place: ['unsupported'] } }, request_id: 'test-request' }, { status });
    await assert.rejects(compare(defaults, 'balanced'), (error: unknown) => error instanceof ModelError && error.kind === kind && error.requestId === 'test-request');
  }
  globalThis.fetch = async () => new Response('<html>Waking service</html>', { status: 502 });
  await assert.rejects(getCatalog(), (error: unknown) => error instanceof ModelError && error.kind === 'network');
});

test('active English and Tagalog copy has no prototype or disconnected-model claims', () => {
  for (const language of ['en', 'tl'] as const) {
    const copy = messages(language);
    assert.doesNotMatch(JSON.stringify(copy), /prototype|interactive demo|sample results|sample numbers|not connected|halimbawang numero|hindi pa nakakonekta/i);
  }
});

test('expanded model preserves its verdict, whole schedules and missing checks', () => {
  const catalog = parseCatalog(expandedCatalog), comparison = parseComparison(expandedComparison);
  assert.equal(catalog.places.length, 22);
  assert.equal(catalog.crops.length, 29);
  assert.ok(catalog.capabilities?.includes('fallow'));
  assert.equal(cropOptions(comparison, catalog, 'balanced').length, 29);
  const field = comparison.results.fields.rain;
  assert.deepEqual(field.recommendation?.suitable, ['radish', 'mungbean']);
  assert.equal(cropFit(field.crops.maize, []), 'partial');
  assert.equal(cropFit(field.crops.sweetpotato, []), 'partial');
  assert.equal(field.schedule?.mungbean.total_days, 50);
  assert.equal(field.crops.mungbean.median_S?.short.balanced, expandedComparison.results.fields.rain.crops.mungbean.median_S.short.balanced);
  const fallow = parseComparison(fallowComparison).results.fields.rain;
  assert.equal(fallow.recommendation?.status, 'none');
  assert.deepEqual(fallow.recommendation?.suitable, []);
  assert.deepEqual(fallow.same_family_as_main, []);
  assert.equal(fallow.schedule?.mungbean.total_days, 92);
  assert.equal(fallow.schedule?.mungbean.spare_days, 105);
});

test('schedule input bounds match the API and a fallow field remains fallow', () => {
  const payload = toModelInputs({ ...defaults, main_crop: 'fallow', prep_days: '14', picking_days: '21', turnaround_days: '7' }, 'balanced');
  assert.equal(payload.main_crop, 'fallow');
  assert.deepEqual([payload.prep_days, payload.picking_days, payload.turnaround_days], [14, 21, 7]);
  for (const value of ['', '-1', '181', '1.5', 'Infinity']) {
    assert.equal(validateInputs({ ...defaults, prep_days: value }), 'prepDays');
    assert.equal(validateInputs({ ...defaults, picking_days: value }), 'pickingDays');
  }
});

test('invalid new evidence and a recommendation containing a partially checked crop are rejected', () => {
  const partial = structuredClone(expandedComparison);
  partial.results.fields.rain.recommendation.suitable.push('maize');
  assert.throws(() => parseComparison(partial), ModelError);
  const plan = structuredClone(expandedComparison);
  plan.results.fields.rain.schedule.mungbean.spare_days++;
  assert.throws(() => parseComparison(plan), ModelError);
  const verdict = structuredClone(fallowComparison);
  verdict.results.fields.rain.recommendation.status = 'suitable';
  assert.throws(() => parseComparison(verdict), ModelError);
  const stale = structuredClone(fallowComparison);
  stale.results.meta.prep_days = 0;
  assert.throws(() => parseComparison(stale), ModelError);
  const rating = structuredClone(expandedComparison);
  rating.results.fields.rain.crops.mungbean.median_S.short.balanced = 1.5;
  assert.throws(() => parseComparison(rating), ModelError);
});
