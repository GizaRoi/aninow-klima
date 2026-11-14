import tagalog from './messages.tl.json';
import type { Inputs, Result } from './demo';

export type Language = 'en' | 'tl';
export type TranslationValues = Record<string, string | number>;
const messages: Record<string, string> = tagalog;

export function translate(text: string, language: Language, values: TranslationValues = {}) {
  const translated = language === 'tl' ? messages[text] ?? text : text;
  return translated.replace(/\{(\w+)\}/g, (match, key: string) => values[key] === undefined ? match : String(values[key]));
}

export type DisplayResult = Omit<Result, 'name' | 'localName' | 'kind' | 'description' | 'rotationNote'> & {
  name: string; localName: string; kind: string; description: string; rotationNote: string;
};

export function localizeResult(result: Result, inputs: Inputs, language: Language): DisplayResult {
  if (language === 'en') return result;
  const t = (text: string, values?: TranslationValues) => translate(text, language, values);
  const checks = result.checks.map(check => {
    let detail = t(check.detail);
    if (check.label === 'Water availability') detail = t('{supply} mm of demo irrigation supply; {need} mm assumed need. These are fictional, like-for-like cycle totals.', { supply: { limited: 200, reliable: 800, none: 0 }[inputs.water], need: result.irrigationMm });
    if (check.label === 'Return-to-rice date') detail = t('Illustrative field-release date: {date}, including {days} assumed preparation days.', { date: result.releaseDate, days: result.turnaroundDays });
    if (check.label === 'Starting budget') detail = t('PHP {cost} assumed upfront cost against PHP {budget} allocated. Later expenses are separate.', { cost: result.upfront.toLocaleString('fil-PH'), budget: inputs.budget.toLocaleString('fil-PH') });
    return { ...check, label: t(check.label), detail };
  });
  return { ...result, checks, name: t(result.name), localName: result.name, kind: t(result.kind), description: t(result.description), rotationNote: t(result.rotationNote) };
}
