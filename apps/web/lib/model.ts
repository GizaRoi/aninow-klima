// HTTP contract served by feat/klima-model. No sample fallback or client scoring.
export { dateLabel, format } from './preview';
export type { Language } from './preview';
export type Season = 'all' | 'normal' | 'dry' | 'el_nino';
export type Priority = 'balanced' | 'saving_water' | 'healthier_soil' | 'finishing_early';
export type FieldInputs = {
  place: string; main_crop: string; harvest: string; next_planting: string;
  drainage: 'well_drained' | 'poorly_drained' | 'unknown'; water: 'rain' | 'irrigation';
  soil_ph: string; soil_texture: '' | 'light' | 'medium' | 'heavy';
  prep_days: string; picking_days: string; turnaround_days: string; pass_mark: string;
};
export type ModelInputs = Omit<FieldInputs, 'soil_ph' | 'soil_texture' | 'prep_days' | 'picking_days' | 'turnaround_days' | 'pass_mark'> & {
  soil_ph: number | null; soil_texture: 'light' | 'medium' | 'heavy' | null;
  prep_days: number; picking_days: number; turnaround_days: number; pass_mark: number; priority: Priority;
};
export type Catalog = {
  contract_version: string; model_version: string;
  capabilities?: string[];
  places: { id: string; name: string; province: string }[];
  crops: { id: string; name: string; local_name: string; limits_basis: string }[];
  drainage: string[]; soil_texture: string[]; water: string[]; priorities: string[]; season_groups: string[];
};
export type History = { pass: number; of: number; not_scored: number; wilson95: [number | null, number | null] };
export type Condition = 'temp' | 'water' | 'ph' | 'texture';
export type ModelCrop = {
  flags: string[]; scored_days: { short: number; long: number };
  median_scores: { short: Record<Condition, number | null> };
  median_deficit_mm: { short: number | null };
  counts: { balanced: Record<Season, { short: History }> };
  drainage_requirement: string; limits_source: string; cycle_source: string;
  not_scored?: Condition[]; family?: string | null;
  guide_check?: { median_temp_c: number; guide_temp_c: [number, number]; outside: 'warmer' | 'cooler' | null } | null;
};
export type Schedule = { prep_days: number; growing_days: number; picking_days: number; clearing_days: number; total_days: number; window_days: number; spare_days: number; fits: boolean };
export type Recommendation = { status: 'suitable' | 'none'; suitable: string[]; rule: string; crops_checked: number; crops_ruled_out: number; held_back_by: Condition[]; partly_checked: string[] };
export type PlantingDate = { offset_days: number; cycle_days: number; scored_seasons: number; of_seasons: number; median_deficit_mm: number | null; median_rws: number | null };
export type ModelField = {
  crops: Record<string, ModelCrop>; excluded: Record<string, string[]>; rankings: Record<Priority, string[]>;
  recommendation?: Recommendation; schedule?: Record<string, Schedule>; same_family_as_main?: string[];
};
export type Comparison = {
  contract_version: string; mode: 'rules_model'; model_version: string; request_id: string;
  inputs: ModelInputs; ranking: string[]; warnings: string[];
  results: {
    meta: { window_days: number; turnaround_days: number; prep_days?: number; picking_days?: number; pass_mark: number; main_crop: string };
    soil: { ph: number | null; texture: string | null; source: string; sample: { sample_id: string; distance_km: number } | null };
    fields: Record<'rain' | 'irrigation', ModelField>;
    crop_coefficients: Record<string, { source: string }>;
    planting_dates?: Record<string, PlantingDate[]>;
  };
};
export const defaults: FieldInputs = {
  place: 'Science City of Muñoz, Nueva Ecija', main_crop: 'rice',
  harvest: '2026-11-15', next_planting: '2027-05-31', drainage: 'well_drained', water: 'rain',
  soil_ph: '', soil_texture: '', prep_days: '0', picking_days: '0', turnaround_days: '0', pass_mark: '0.6',
};
export const API_BASE = (process.env.NEXT_PUBLIC_KLIMA_API_URL || 'https://aninow-klima.onrender.com').replace(/\/+$/, '');
const CONTRACT = 'klima-comparison.v1';
const seasons: Season[] = ['all', 'normal', 'dry', 'el_nino'];
const priorities: Priority[] = ['balanced', 'saving_water', 'healthier_soil', 'finishing_early'];
function validDate(value: string) {
  const parsed = new Date(`${value}T00:00:00Z`);
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}
export function windowDays(inputs: FieldInputs) {
  return validDate(inputs.harvest) && validDate(inputs.next_planting)
    ? Math.max(0, Math.round((Date.parse(inputs.next_planting) - Date.parse(inputs.harvest)) / 86400000)) : 0;
}
export function validateInputs(inputs: FieldInputs) {
  if (!validDate(inputs.harvest) || !validDate(inputs.next_planting)) return 'dates';
  if (inputs.harvest.slice(5) === '02-29' || inputs.next_planting.slice(5) === '02-29') return 'leap';
  if (windowDays(inputs) <= 0) return 'order';
  const expectedYear = Number(inputs.harvest.slice(0, 4)) + Number(inputs.next_planting.slice(5) <= inputs.harvest.slice(5));
  if (Number(inputs.next_planting.slice(0, 4)) !== expectedYear) return 'annual';
  if (inputs.soil_ph.trim() && (!Number.isFinite(Number(inputs.soil_ph)) || Number(inputs.soil_ph) < 3 || Number(inputs.soil_ph) > 10)) return 'ph';
  if (!inputs.prep_days.trim() || !Number.isInteger(Number(inputs.prep_days)) || Number(inputs.prep_days) < 0 || Number(inputs.prep_days) > 180) return 'prepDays';
  if (!inputs.picking_days.trim() || !Number.isInteger(Number(inputs.picking_days)) || Number(inputs.picking_days) < 0 || Number(inputs.picking_days) > 180) return 'pickingDays';
  if (!inputs.turnaround_days.trim() || !Number.isInteger(Number(inputs.turnaround_days)) || Number(inputs.turnaround_days) < 0 || Number(inputs.turnaround_days) > 90) return 'preparation';
  if (!inputs.pass_mark.trim() || !Number.isFinite(Number(inputs.pass_mark)) || Number(inputs.pass_mark) < 0 || Number(inputs.pass_mark) > 1) return 'passMark';
  return null;
}
export function toModelInputs(inputs: FieldInputs, priority: Priority): ModelInputs {
  const error = validateInputs(inputs);
  if (error) throw new Error(error);
  return { ...inputs, soil_ph: inputs.soil_ph.trim() ? Number(inputs.soil_ph) : null,
    soil_texture: inputs.soil_texture || null, prep_days: Number(inputs.prep_days), picking_days: Number(inputs.picking_days), turnaround_days: Number(inputs.turnaround_days), pass_mark: Number(inputs.pass_mark), priority };
}
export class ModelError extends Error {
  constructor(public kind: 'network' | 'busy' | 'timeout' | 'validation' | 'contract', public fields: Record<string, string[]> = {}, public requestId = '') { super(kind); }
}
const record = (value: unknown): value is Record<string, any> => !!value && typeof value === 'object' && !Array.isArray(value);
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(item => typeof item === 'string');
const numeric = (value: unknown) => typeof value === 'number' && Number.isFinite(value);
const nullableNumber = (value: unknown) => value === null || numeric(value);
export function parseCatalog(value: unknown): Catalog {
  if (!record(value) || value.contract_version !== CONTRACT || typeof value.model_version !== 'string' ||
    (value.capabilities !== undefined && !strings(value.capabilities)) ||
    !Array.isArray(value.places) || !value.places.length || !value.places.every((p: any) => record(p) && ['id', 'name', 'province'].every(k => typeof p[k] === 'string')) ||
    !Array.isArray(value.crops) || !value.crops.length || !value.crops.every((c: any) => record(c) && ['id', 'name', 'local_name', 'limits_basis'].every(k => typeof c[k] === 'string')) ||
    !['drainage', 'soil_texture', 'water', 'priorities', 'season_groups'].every(k => strings(value[k])) ||
    !seasons.every(s => value.season_groups.includes(s)) || !priorities.every(p => value.priorities.includes(p))) throw new ModelError('contract');
  return value as Catalog;
}
export function parseComparison(value: unknown): Comparison {
  if (!record(value) || value.contract_version !== CONTRACT || value.mode !== 'rules_model' ||
    typeof value.model_version !== 'string' || typeof value.request_id !== 'string' || !strings(value.ranking) || !strings(value.warnings) ||
    !record(value.inputs) || !['rain', 'irrigation'].includes(value.inputs.water) || !['well_drained', 'poorly_drained', 'unknown'].includes(value.inputs.drainage) || !priorities.includes(value.inputs.priority) ||
    !numeric(value.inputs.pass_mark) || !Number.isInteger(value.inputs.turnaround_days) || typeof value.inputs.main_crop !== 'string' || !record(value.results) ||
    !record(value.results.meta) || !numeric(value.results.meta.window_days) || value.results.meta.window_days <= 0 || !record(value.results.soil) ||
    !nullableNumber(value.results.soil.ph) || !(value.results.soil.texture === null || ['light', 'medium', 'heavy'].includes(value.results.soil.texture)) ||
    typeof value.results.soil.source !== 'string' || !record(value.results.fields) || !record(value.results.crop_coefficients)) throw new ModelError('contract');
  for (const water of ['rain', 'irrigation']) {
    const field = value.results.fields[water];
    if (!record(field) || !record(field.crops) || !record(field.excluded) || !Object.values(field.excluded).every(strings) ||
      !record(field.rankings) || !priorities.every(p => strings(field.rankings[p]) && new Set(field.rankings[p]).size === Object.keys(field.crops).length &&
        field.rankings[p].length === Object.keys(field.crops).length && field.rankings[p].every((id: string) => record(field.crops[id]) && !field.excluded[id]))) throw new ModelError('contract');
    if (field.recommendation !== undefined) {
      const verdict = field.recommendation;
      if (!record(verdict) || !['suitable', 'none'].includes(verdict.status) || !strings(verdict.suitable) ||
        !strings(verdict.partly_checked) || !strings(verdict.held_back_by) || !verdict.held_back_by.every(k => ['temp', 'water', 'ph', 'texture'].includes(k)) ||
        typeof verdict.rule !== 'string' || !Number.isInteger(verdict.crops_checked) || !Number.isInteger(verdict.crops_ruled_out) ||
        (verdict.status === 'none') !== (verdict.suitable.length === 0) ||
        ![...verdict.suitable, ...verdict.partly_checked].every(id => record(field.crops[id])) ||
        verdict.suitable.some(id => verdict.partly_checked.includes(id) || field.crops[id].not_scored?.length)) throw new ModelError('contract');
    }
    if (field.same_family_as_main !== undefined && !strings(field.same_family_as_main)) throw new ModelError('contract');
    if (field.schedule !== undefined) {
      if (!record(field.schedule) || value.results.meta.main_crop !== value.inputs.main_crop ||
        (value.inputs.prep_days !== undefined && (!Number.isInteger(value.inputs.prep_days) || value.results.meta.prep_days !== value.inputs.prep_days)) ||
        (value.inputs.picking_days !== undefined && (!Number.isInteger(value.inputs.picking_days) || value.results.meta.picking_days !== value.inputs.picking_days)) ||
        value.results.meta.turnaround_days !== value.inputs.turnaround_days || ![...Object.keys(field.crops), ...Object.keys(field.excluded)].every(id => {
        const plan = field.schedule[id];
        return record(plan) && ['prep_days', 'growing_days', 'picking_days', 'clearing_days', 'total_days', 'window_days', 'spare_days'].every(k => Number.isInteger(plan[k])) &&
          ['prep_days', 'growing_days', 'picking_days', 'clearing_days', 'total_days', 'window_days'].every(k => plan[k] >= 0) &&
          plan.prep_days === value.results.meta.prep_days && plan.picking_days === value.results.meta.picking_days &&
          plan.clearing_days === value.inputs.turnaround_days && plan.window_days === value.results.meta.window_days &&
          typeof plan.fits === 'boolean' && plan.total_days === plan.prep_days + plan.growing_days + plan.picking_days + plan.clearing_days &&
          plan.spare_days === plan.window_days - plan.total_days && plan.fits === (plan.spare_days >= 0);
      })) throw new ModelError('contract');
    }
    for (const crop of Object.values(field.crops)) {
      if (!record(crop) || !strings(crop.flags) || !['drainage_requirement', 'limits_source', 'cycle_source'].every(k => typeof crop[k] === 'string') ||
        !record(crop.scored_days) || !numeric(crop.scored_days.short) || crop.scored_days.short <= 0 || !numeric(crop.scored_days.long) ||
        !record(crop.median_scores?.short) || !['temp', 'water', 'ph', 'texture'].every(k => nullableNumber(crop.median_scores.short[k])) ||
        !nullableNumber(crop.median_deficit_mm?.short) || !record(crop.counts?.balanced) || !seasons.every(s => {
          const count = crop.counts.balanced[s]?.short;
          return record(count) && Number.isInteger(count.pass) && Number.isInteger(count.of) && count.pass >= 0 && count.pass <= count.of && Number.isInteger(count.not_scored) &&
            Array.isArray(count.wilson95) && count.wilson95.length === 2 && count.wilson95.every(nullableNumber);
        })) throw new ModelError('contract');
      if ((crop.not_scored !== undefined && (!strings(crop.not_scored) || !crop.not_scored.every(k => ['temp', 'water', 'ph', 'texture'].includes(k)))) ||
        (crop.family !== undefined && crop.family !== null && typeof crop.family !== 'string')) throw new ModelError('contract');
      if (crop.guide_check != null && (!record(crop.guide_check) || !numeric(crop.guide_check.median_temp_c) ||
        !Array.isArray(crop.guide_check.guide_temp_c) || crop.guide_check.guide_temp_c.length !== 2 || !crop.guide_check.guide_temp_c.every(numeric) ||
        ![null, 'warmer', 'cooler'].includes(crop.guide_check.outside))) throw new ModelError('contract');
    }
  }
  if (value.results.planting_dates !== undefined && (!record(value.results.planting_dates) || !Object.values(value.results.planting_dates).every(entries =>
    Array.isArray(entries) && entries.every(entry => record(entry) && ['offset_days', 'cycle_days', 'scored_seasons', 'of_seasons'].every(k => Number.isInteger(entry[k])) &&
      nullableNumber(entry.median_deficit_mm) && nullableNumber(entry.median_rws))))) throw new ModelError('contract');
  return value as Comparison;
}
export function cropFit(result: ModelCrop | null, excluded: string[]) {
  if (excluded.length) return 'out';
  if (result?.not_scored?.length) return 'partial';
  const values = Object.values(result?.median_scores.short ?? {}).filter((value): value is number => value !== null);
  if (!values.length) return null;
  const weakest = Math.min(...values);
  return weakest >= .7 ? 'good' : weakest >= .45 ? 'ok' : 'poor';
}
async function request(path: string, init: RequestInit = {}) {
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...init, cache: 'no-store', signal: init.signal
      ? AbortSignal.any([init.signal, AbortSignal.timeout(180_000)]) : AbortSignal.timeout(180_000) });
    let body;
    try { body = await response.json(); } catch { throw new ModelError(response.ok ? 'contract' : 'network'); }
    if (!record(body)) throw new ModelError(response.ok ? 'contract' : 'network');
    if (!response.ok) throw new ModelError(response.status === 422 ? 'validation' : response.status === 503 ? 'busy' : response.status === 504 ? 'timeout' : 'network',
      record(body.error?.field_errors) && Object.values(body.error.field_errors).every(strings) ? body.error.field_errors : {}, typeof body.request_id === 'string' ? body.request_id : '');
    return body;
  } catch (error) {
    if (error instanceof ModelError) throw error;
    throw new ModelError(error instanceof Error && error.name === 'TimeoutError' ? 'timeout' : 'network');
  }
}
export async function getCatalog(signal?: AbortSignal) { return parseCatalog(await request('/api/v1/catalog', { signal })); }
export async function compare(inputs: FieldInputs, priority: Priority, signal?: AbortSignal) {
  return parseComparison(await request('/api/v1/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toModelInputs(inputs, priority)), signal }));
}
export function cropOptions(comparison: Comparison, catalog: Catalog, priority: Priority) {
  const field = comparison.results.fields[comparison.inputs.water];
  const order = [...field.rankings[priority], ...Object.keys(field.excluded)];
  return order.map(id => {
    const crop = catalog.crops.find(c => c.id === id);
    if (!crop) throw new ModelError('contract');
    return { crop, result: field.crops[id] ?? null, excluded: field.excluded[id] ?? [] };
  });
}
