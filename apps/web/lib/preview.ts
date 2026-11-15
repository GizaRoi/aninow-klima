import cropData from './sample-crops.json';
import weights from './sample-weights.json';

// UI fixtures from the supplied HTML. This adapter never invokes the Python model.
export type Language = 'en' | 'tl';
export type Season = 'typical' | 'dry' | 'nino';
export type Priority = 'even' | 'water' | 'soil' | 'time';
export type Soil = 'clayloam' | 'clay' | 'siltloam' | 'sandyloam' | '';
export type FieldInputs = {
  soil: Soil;
  pond: 'no' | 'yes' | 'unsure';
  water: 'rain' | 'irrig';
  harvest: string;
  next: string;
  ph: string;
};
export type Condition = 'temp' | 'rain' | 'moist' | 'ph' | 'tex' | 'time';
export type Crop = (typeof cropData)[number];
export type CropOption = {
  crop: Crop;
  fit: 'good' | 'ok' | 'poor' | 'out';
  index: number | null;
  blocked: 'pond' | 'days' | null;
  checkDrainage: boolean;
  conditions: Partial<Record<Condition, number>>;
  missing: ('need' | 'ph' | 'tex')[];
  history: number[];
};
export type PreviewComparison = {
  mode: 'sample';
  source: 'supplied-html';
  inputs: FieldInputs;
  season: Season;
  priority: Priority;
  days: number;
  options: CropOption[];
};

export const defaults: FieldInputs = {
  soil: 'clayloam', pond: 'no', water: 'rain',
  harvest: '2026-11-15', next: '2027-05-31', ph: '',
};

function validDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function windowDays(inputs: FieldInputs) {
  if (!validDate(inputs.harvest) || !validDate(inputs.next)) return 0;
  return Math.max(0, Math.round((Date.parse(inputs.next) - Date.parse(inputs.harvest)) / 86400000));
}

export function validateInputs(inputs: FieldInputs): 'dates' | 'order' | 'ph' | null {
  if (!validDate(inputs.harvest) || !validDate(inputs.next)) return 'dates';
  if (windowDays(inputs) <= 0) return 'order';
  if (inputs.ph.trim() && (!Number.isFinite(Number(inputs.ph)) || Number(inputs.ph) < 3 || Number(inputs.ph) > 10)) return 'ph';
  return null;
}

// Preserves the HTML's illustrative scoring, not the model's scoring method.
export function getPreviewComparison(inputs: FieldInputs, season: Season, priority: Priority): PreviewComparison {
  const error = validateInputs(inputs);
  if (error) throw new Error(`Invalid field inputs: ${error}`);
  const days = windowDays(inputs);
  const options: CropOption[] = cropData.map(crop => {
    const blocked = !crop.wet && inputs.pond === 'yes' ? 'pond' : crop.days > days ? 'days' : null;
    if (blocked) return { crop, fit: 'out', index: null, blocked, checkDrainage: false, conditions: {}, missing: [], history: [] };
    const scores: Partial<Record<Condition | 'soil', number>> = {
      temp: crop.temp[season], rain: inputs.water === 'irrig' ? .9 : crop.rain[season],
      moist: inputs.water === 'irrig' ? .9 : crop.moist[season], soil: crop.soil, time: 1 - crop.days / days,
    };
    const missing: CropOption['missing'] = ['need'];
    if (inputs.soil) scores.tex = crop.tex[inputs.soil]; else missing.push('tex');
    if (inputs.ph.trim()) {
      const ph = Number(inputs.ph), [lo, hi] = crop.ph;
      scores.ph = Math.max(0, 1 - Math.max(lo - ph, ph - hi, 0));
    } else missing.push('ph');
    let sum = 0, total = 0;
    for (const key of Object.keys(scores) as (keyof typeof scores)[]) {
      sum += weights[priority][key] * scores[key]!;
      total += weights[priority][key];
    }
    const index = sum / total;
    const { soil: _soil, ...conditions } = scores;
    return { crop, index, fit: index >= .7 ? 'good' : index >= .5 ? 'ok' : 'poor', blocked: null,
      checkDrainage: !crop.wet && inputs.pond === 'unsure', conditions, missing, history: crop.hist[inputs.water][season] };
  });
  options.sort((a, b) => (b.index ?? -1) - (a.index ?? -1));
  return { mode: 'sample', source: 'supplied-html', inputs: { ...inputs }, season, priority, days, options };
}

export function dateLabel(value: string, language: Language) {
  if (!validDate(value)) return '—';
  return new Intl.DateTimeFormat(language === 'tl' ? 'fil-PH' : 'en-PH', {
    month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  }).format(new Date(`${value}T00:00:00Z`));
}

export function format(template: string, values: Record<string, string | number>) {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? `{${key}}`));
}
