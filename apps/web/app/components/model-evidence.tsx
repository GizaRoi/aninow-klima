import { Info } from 'lucide-react';
import { dateLabel, format, type Catalog, type Comparison, type Language, type Schedule } from '../../lib/model';
import type { Messages } from '../../lib/messages';

export function RecommendationNotice({ comparison, catalog, language, m }: { comparison: Comparison; catalog: Catalog; language: Language; m: Messages }) {
  const verdict = comparison.results.fields[comparison.inputs.water].recommendation;
  if (!verdict) return null;
  const names = verdict.suitable.map(id => {
    const crop = catalog.crops.find(c => c.id === id);
    return crop ? language === 'en' ? crop.name : crop.local_name : id;
  });
  return <section className={`recommendation-notice ${verdict.status === 'none' ? 'recommendation-none' : ''}`} aria-labelledby="recommendation-title">
    <Info size={22}/><div><h3 id="recommendation-title">{verdict.status === 'none' ? m.noneTitle : m.suitableTitle}</h3>
      {names.length > 0 && <p className="recommendation-crops">{names.join(' · ')}</p>}
      <p>{format(m.suitableRule, { mark: comparison.inputs.pass_mark })}</p>
      {verdict.status === 'none' && <p>{m.noneCopy}</p>}
      {verdict.held_back_by.length > 0 && <p>{format(m.heldBack, { conditions: verdict.held_back_by.map(key => m.conditions[key]).join(', ') })}</p>}
    </div>
  </section>;
}

export function WholeSchedule({ plan, m }: { plan: Schedule; m: Messages }) {
  return <div className="whole-schedule"><h4>{m.schedule} <span>{format(m.totalDays, { n: plan.total_days })}</span></h4>
    <dl>{[[m.prepDays, plan.prep_days], [m.growing, plan.growing_days], [m.pickingDays, plan.picking_days], [m.clearingDays, plan.clearing_days]].map(([label, days]) =>
      <div key={label}><dt>{label}</dt><dd>{days} {m.daysUnit}</dd></div>)}</dl>
  </div>;
}

export function PlantingDates({ comparison, cropId, language, m }: { comparison: Comparison; cropId: string; language: Language; m: Messages }) {
  const entries = comparison.results.planting_dates?.[cropId];
  if (!entries?.length) return null;
  const start = (offset: number) => {
    const date = new Date(`${comparison.inputs.harvest}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() + offset);
    return dateLabel(date.toISOString().slice(0, 10), language);
  };
  return <><h4>{m.plantingDates}</h4><p>{m.plantingDatesNote}</p><div className="planting-table" tabIndex={0} role="region" aria-label={m.plantingDates}><table>
    <caption className="sr-only">{m.plantingDates}</caption><thead><tr><th scope="col">{m.plantingStart}</th><th scope="col">{m.waterGap}</th><th scope="col">{m.rainCoverage}</th><th scope="col">{m.seasonsChecked}</th></tr></thead>
    <tbody>{entries.map(entry => <tr key={entry.offset_days}><th scope="row">{start(entry.offset_days)}</th><td>{entry.median_deficit_mm === null ? m.unknown : `${Math.round(entry.median_deficit_mm)} mm`}</td><td>{entry.median_rws === null ? m.unknown : `${Math.round(entry.median_rws * 100)}%`}</td><td>{entry.scored_seasons}/{entry.of_seasons}</td></tr>)}</tbody>
  </table></div></>;
}
