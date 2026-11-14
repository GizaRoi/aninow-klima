/** Entirely synthetic software fixtures. These are not crop profiles or NASA observations. */
export type Priority = 'water_security' | 'upfront_affordability' | 'calendar_fit' | 'soil_care' | 'income';
export type Inputs = {
  area: number;
  plantingDate: string;
  riceDeadline: string;
  budget: number;
  water: 'limited' | 'reliable' | 'none';
  drainage: 'unknown' | 'well_drained' | 'waterlogging';
  buyer: 'unknown' | 'available' | 'unavailable';
  priority: Priority;
  simulation: boolean;
  ricePrice: number;
  mungbeanPrice: number;
};
export const defaults: Inputs = {
  area: 1, plantingDate: '2027-01-15', riceDeadline: '2027-05-31', budget: 35000,
  water: 'limited', drainage: 'unknown', buyer: 'unknown', priority: 'water_security',
  simulation: false, ricePrice: 22, mungbeanPrice: 65,
};
export const priorities: { id: Priority; label: string; description: string }[] = [
  { id: 'water_security', label: 'Save water', description: 'Work with the water I have' },
  { id: 'upfront_affordability', label: 'Spend less upfront', description: 'Keep starting costs manageable' },
  { id: 'calendar_fit', label: 'Fit my calendar', description: 'Be ready for rice again on time' },
  { id: 'soil_care', label: 'Care for my soil', description: 'Explore rotation tradeoffs' },
  { id: 'income', label: 'Explore income', description: 'Compare explicit money scenarios' },
];
export const fixtures = [
  { id: 'rice', name: 'Rice', localName: 'Palay', kind: 'Your usual crop', occupationDays: 115, turnaroundDays: 10, irrigationMm: 650, yieldKgHa: 4800, costPerHa: 68000, upfrontPerHa: 36000,
    description: 'Continue with the crop you know. Check whether your water supply can support another planting.',
    rotationNote: 'Repeating rice keeps the sequence familiar. Any soil or management benefit needs local evidence.' },
  { id: 'mungbean', name: 'Mungbean', localName: 'Munggo', kind: 'Rotation to explore', occupationDays: 65, turnaroundDays: 10, irrigationMm: 140, yieldKgHa: 900, costPerHa: 27000, upfrontPerHa: 16000,
    description: 'Explore a different crop after rice, subject to drainage, a suitable planting window, and a buyer.',
    rotationNote: 'A different crop adds diversity to the sequence. Nutrient benefits depend on local management and residue handling.' },
] as const;

export type Check = { label: string; status: 'pass' | 'fail' | 'unknown'; detail: string };
export function addDays(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
export function validateInputs(input: Inputs): string | null {
  if (!['limited', 'reliable', 'none'].includes(input.water) || !['unknown', 'well_drained', 'waterlogging'].includes(input.drainage) || !['unknown', 'available', 'unavailable'].includes(input.buyer) || !priorities.some(p => p.id === input.priority) || typeof input.simulation !== 'boolean') return 'Choose valid demo water, drainage, buyer, and priority settings.';
  if (!Number.isFinite(input.area) || input.area <= 0 || input.area > 10) return 'Enter a field area greater than 0 and no larger than 10 hectares for this demo.';
  if (!Number.isFinite(input.budget) || input.budget < 0) return 'Enter a valid, nonnegative starting budget.';
  for (const date of [input.plantingDate, input.riceDeadline]) {
    const d = new Date(`${date}T00:00:00Z`);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(d.valueOf()) || d.toISOString().slice(0, 10) !== date) return 'Choose valid planting and return-to-rice dates.';
  }
  if (input.riceDeadline <= input.plantingDate) return 'The return-to-rice date must be after the proposed planting date.';
  if (![input.ricePrice, input.mungbeanPrice].every(p => Number.isFinite(p) && p >= 0)) return 'Selling prices must be valid, nonnegative amounts.';
  return null;
}

export function evaluate(input: Inputs) {
  const error = validateInputs(input);
  if (error) throw new Error(error);
  const supply = { limited: 200, reliable: 800, none: 0 }[input.water];
  return fixtures.map(crop => {
    const releaseDate = addDays(input.plantingDate, crop.occupationDays + crop.turnaroundDays);
    const upfront = Math.round(crop.upfrontPerHa * input.area);
    const totalCost = Math.round(crop.costPerHa * input.area);
    const checks: Check[] = [
      { label: 'Water availability', status: supply >= crop.irrigationMm ? 'pass' : 'fail', detail: `${supply} mm of demo irrigation supply; ${crop.irrigationMm} mm assumed need. These are fictional, like-for-like cycle totals.` },
      { label: 'Return-to-rice date', status: releaseDate <= input.riceDeadline ? 'pass' : 'fail', detail: `Illustrative field-release date: ${releaseDate}, including ${crop.turnaroundDays} assumed preparation days.` },
      { label: 'Starting budget', status: upfront <= input.budget ? 'pass' : 'fail', detail: `PHP ${upfront.toLocaleString('en-PH')} assumed upfront cost against PHP ${input.budget.toLocaleString('en-PH')} allocated. Later expenses are separate.` },
      { label: 'Field drainage', status: crop.id === 'rice' ? 'pass' : input.drainage === 'unknown' ? 'unknown' : input.drainage === 'waterlogging' ? 'fail' : 'pass', detail: crop.id === 'rice' ? 'No extra drainage requirement in this simplified fixture; real rice suitability is not evaluated.' : input.drainage === 'unknown' ? 'Confirm drainage with a local agricultural adviser before considering this option.' : 'This is a simplified demo check, not a validated soil assessment.' },
      { label: 'Buyer access', status: input.buyer === 'available' ? 'pass' : input.buyer === 'unavailable' ? 'fail' : 'unknown', detail: input.buyer === 'available' ? 'Buyer marked available for this example. The selling price remains an assumption.' : 'Confirm a buyer for this crop; availability is not inferred from climate suitability.' },
    ];
    const feasibility = checks.some(c => c.status === 'fail') ? 'infeasible' : checks.some(c => c.status === 'unknown') ? 'unknown' : 'feasible';
    const yieldKg = input.simulation ? Math.round(crop.yieldKgHa * input.area) : null;
    const price = crop.id === 'rice' ? input.ricePrice : input.mungbeanPrice;
    const revenue = yieldKg === null ? null : Math.round(yieldKg * price * 100) / 100;
    return { ...crop, releaseDate, upfront, totalCost, checks, feasibility, yieldKg, price, revenue, netIncome: revenue === null ? null : revenue - totalCost, estimateBasis: input.simulation ? 'simulation' : 'unavailable' };
  });
}
export type Result = ReturnType<typeof evaluate>[number];
export type SavedPlan = { id: string; savedAt: string; inputs: Inputs };
export function php(value: number): string {
  return new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP', maximumFractionDigits: 0 }).format(value);
}
export function dateLabel(value: string, language: 'en' | 'tl' = 'en'): string {
  return new Intl.DateTimeFormat(language === 'tl' ? 'fil-PH' : 'en-PH', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`));
}
