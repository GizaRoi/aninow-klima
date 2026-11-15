import { ArrowRight, CalendarDays, ChevronDown, MapPin } from 'lucide-react';
import { dateLabel, format, type Catalog, type Comparison, type Language } from '../../lib/model';
import type { Messages } from '../../lib/messages';

export function ResultOverview({ comparison, catalog, language, m }: { comparison: Comparison; catalog: Catalog; language: Language; m: Messages }) {
  const { inputs, results } = comparison;
  const crop = catalog.crops.find(c => c.id === inputs.main_crop);
  const cropName = inputs.main_crop === 'fallow' ? m.fallow : crop ? language === 'en' ? crop.name : crop.local_name : inputs.main_crop;
  return <section className="result-window" aria-labelledby="window-title">
    <div className="result-window-heading"><span className="result-window-icon"><CalendarDays size={24}/></span><div>
      <h3 id="window-title">{format(inputs.main_crop === 'fallow' ? m.fallowWin : m.win, { n: results.meta.window_days })}</h3>
      <p>{dateLabel(inputs.harvest, language)} <ArrowRight size={13}/> {dateLabel(inputs.next_planting, language)}<span>·</span><MapPin size={13}/>{inputs.place}</p>
    </div></div>
    <div className="model-context">
      <div className="overview-fields">
        <p>{m.waterSupply}: <strong>{inputs.water === 'irrigation' ? m.w_irrig : m.w_rain}</strong></p>
        <p>{m.drainageLabel}: <strong>{m.drainageAnswers[inputs.drainage]}</strong></p>
        <p>{m.currentCrop}: <strong>{cropName}</strong></p>
        <p>{m.soilUsed}: <strong>{results.soil.ph ?? m.unknown} pH · {results.soil.texture ? m.texture[results.soil.texture as keyof typeof m.texture] ?? m.unknown : m.unknown}</strong></p>
      </div>
      <p className="overview-soil-source">{m.f_ph}: {inputs.soil_ph === null ? m.nearbySample : m.measured} · {m.soilTexture}: {inputs.soil_texture === null ? m.nearbySample : m.measured}</p>
      <dl className="overview-allowances">{[[m.passMark, inputs.pass_mark], [m.prepDays, inputs.prep_days ?? 0], [m.pickingDays, inputs.picking_days ?? 0], [m.clearingDays, inputs.turnaround_days]].map(([label, value], index) => <div key={label}><dt>{label}</dt><dd>{value}{index > 0 && <small> {m.daysUnit}</small>}</dd></div>)}</dl>
      {inputs.water === 'irrigation' && inputs.drainage === 'poorly_drained' && <p className="overview-caution">{m.irrigationDrainageNote}</p>}
      <details className="overview-notes"><summary>{m.calculationNotes}<ChevronDown size={16}/></summary><div><p>{results.soil.source}</p><p>{m.historicalNote}</p>{inputs.water === 'irrigation' && <p>{m.irrigationNote}</p>}{inputs.drainage === 'unknown' && <p>{m.drainageNote}</p>}<p>{m.reviewNote}</p></div></details>
    </div>
  </section>;
}
