import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import expandedComparison from '../../../tests/fixtures/expanded-comparison.json';
import { CropReferences } from '../app/components/crop-references';
import { modelReferences, referencesForCrop } from './model-references';

test('actual expanded model provenance resolves to publications without dropping unfamiliar sources', () => {
  const checked = new Set<string>();
  for (const field of Object.values(expandedComparison.results.fields)) {
    for (const [id, crop] of Object.entries(field.crops)) {
      const coefficient = expandedComparison.results.crop_coefficients[id as keyof typeof expandedComparison.results.crop_coefficients];
      const sources = referencesForCrop(crop, coefficient.source);
      assert.deepEqual(sources.unmatched, [], id);
      assert.ok(sources.references.some(source => source.id === 'fao56'), id);
      assert.ok(sources.references.some(source => source.id.startsWith('ecocrop:')), id);
      assert.equal(new Set(sources.references.map(source => source.id)).size, sources.references.length);
      checked.add(id);
    }
  }
  assert.ok(checked.size >= 20);
  assert.equal(Object.keys(modelReferences).filter(id => id.startsWith('ecocrop:')).length, 29);
});

test('lettuce cites the actual pH and temperature providers alongside its texture sheet', () => {
  const sources = referencesForCrop({
    limits_source: 'DA crop production guide as compiled in crop_requirements_ph.csv (PHV_LETTUCE). Soil texture is scored from FAO EcoCrop sheet 1313.',
    cycle_source: 'FAO-56 Table 11 total of the four stages.',
  }, 'FAO-56 T12 lettuce.');
  assert.deepEqual(sources.unmatched, []);
  assert.deepEqual(new Set(sources.references.map(source => source.id)), new Set([
    'urbanGardening', 'lettuceBicol', 'fao56', 'ecocrop:1313',
  ]));
  assert.equal(sources.references[0].authors, 'Agricultural Training Institute, Cordillera Administrative Region');
  assert.equal(modelReferences.urbanGardening.date, 'n.d.');
  assert.equal(modelReferences.lettuceBicol.date, '2021');
});

test('rice retains the separate paddy manual and variety-selection study exactly once', () => {
  const crop = expandedComparison.results.fields.rain.crops.rice;
  const sources = referencesForCrop(crop, expandedComparison.results.crop_coefficients.rice.source);
  assert.deepEqual(sources.unmatched, []);
  assert.deepEqual(new Set(sources.references.map(source => source.id)), new Set([
    'fao56', 'irrigationManual3', 'ecocrop:1574', 'riceVarieties', 'riceSeedChoice',
  ]));
  assert.equal(modelReferences.irrigationManual3.date, '1986');
  assert.equal(modelReferences.riceSeedChoice.journal?.article, '101227');
});

test('an unrecognized publication or identifier remains visible without invented metadata', () => {
  const unknown = 'FAO-56 Table 11 plus FAO EcoCrop sheet 999999 and a new unpublished local study.';
  const other = 'Local farmer observations with no publication details.';
  const sources = referencesForCrop({ limits_source: unknown, cycle_source: other }, other);
  assert.deepEqual(sources.references.map(source => source.id), ['fao56']);
  assert.deepEqual(sources.unmatched, [unknown, other]);
});

test('a returned guide caution adds its actual source without replacing the global limits', () => {
  const crop = { limits_source: 'FAO EcoCrop sheet 1379.', cycle_source: 'FAO EcoCrop sheet 1379.' };
  assert.equal(referencesForCrop(crop, '').references.length, 1);
  const caution = referencesForCrop({ ...crop, guide_check: {
    median_temp_c: 25, guide_temp_c: [21, 24], outside: 'warmer',
  } }, '');
  assert.deepEqual(new Set(caution.references.map(source => source.id)), new Set(['ecocrop:1379', 'PHV_TOMATO']));
});

test('APA rendering italicizes book and journal titles and preserves author punctuation', () => {
  const crop = expandedComparison.results.fields.rain.crops.rice;
  const html = renderToStaticMarkup(createElement(CropReferences, {
    result: crop, waterSource: expandedComparison.results.crop_coefficients.rice.source, heading: 'Sources',
  }));
  assert.match(html, /Smith, M\. \(1998\)\./);
  assert.doesNotMatch(html, /Smith, M\.\./);
  assert.match(html, /<cite>Crop evapotranspiration: Guidelines for computing crop water requirements<\/cite>/);
  assert.match(html, /<cite>Technology in Society, 60<\/cite>, Article 101227/);
  assert.match(html, /https:\/\/doi.org\/10\.1016\/j\.techsoc\.2019\.101227/);
  assert.match(html, /class="apa-references"/);
  assert.match(html, /Retrieved November 15, 2026, from/);
});
