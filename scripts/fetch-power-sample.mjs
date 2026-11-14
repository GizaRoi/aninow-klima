import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

// Public example point, not a farmer's location or a published pilot boundary.
const url = new URL('https://power.larc.nasa.gov/api/temporal/daily/point');
url.search = new URLSearchParams({ parameters: 'T2M_MAX,PRECTOTCORR', community: 'AG', longitude: '120.59', latitude: '15.48', start: '20240101', end: '20240130', format: 'JSON', 'time-standard': 'UTC' }).toString();
const response = await fetch(url, { signal: AbortSignal.timeout(45000) });
if (!response.ok) throw new Error(`NASA POWER returned HTTP ${response.status}; no existing sample was replaced.`);
const raw = await response.json();
if (raw.parameters?.T2M_MAX?.units !== 'C' || raw.parameters?.PRECTOTCORR?.units !== 'mm/day') throw new Error('NASA sample returned unexpected units.');
const parameters = raw.properties?.parameter;
const maxTemperature = Object.values(parameters?.T2M_MAX ?? {});
const rain = Object.values(parameters?.PRECTOTCORR ?? {});
for (const values of [maxTemperature, rain]) {
  if (values.length !== 30 || values.some(value => typeof value !== 'number' || !Number.isFinite(value) || value === raw.header?.fill_value)) throw new Error('NASA sample has missing or invalid daily values.');
}
if (rain.some(value => value < 0)) throw new Error('Rainfall values cannot be negative.');
const sample = { source: 'NASA POWER Daily API', sourceUrl: url.href, retrievedAt: new Date().toISOString(), start: '2024-01-01', end: '2024-01-30', timeStandard: 'UTC', latitude: 15.48, longitude: 120.59,
  meanDailyMaximumC: Number((maxTemperature.reduce((a,b) => a+b, 0) / 30).toFixed(1)), precipitationTotalMm: Number(rain.reduce((a,b) => a+b, 0).toFixed(1)),
  note: 'Archived regional climate context only. Not a field measurement, forecast, or input to the synthetic crop comparison.', raw };
const destination = fileURLToPath(new URL('../apps/web/lib/power-sample.json', import.meta.url));
await writeFile(destination, JSON.stringify(sample, null, 2) + '\n');
console.log(JSON.stringify({ source: sample.source, period: `${sample.start}/${sample.end}`, temperature: sample.meanDailyMaximumC, rainfall: sample.precipitationTotalMm, units: raw.parameters }));
