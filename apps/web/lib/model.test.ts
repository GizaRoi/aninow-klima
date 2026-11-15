import assert from 'node:assert/strict';
import { test } from 'node:test';
import catalogData from '../../../tests/fixtures/catalog.json';
import comparisonData from '../../../tests/fixtures/comparison.json';
import { compare, cropOptions, defaults, getCatalog, ModelError, parseCatalog, parseComparison, toModelInputs, validateInputs } from './model';
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
  assert.deepEqual(toModelInputs(defaults, 'balanced'), comparisonData.inputs);
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
    assert.deepEqual(JSON.parse(String(init?.body)), comparisonData.inputs);
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
