'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, CalendarDays, Check, ChevronDown, CircleHelp, CloudRain, Download, Droplets, Earth, Info, Leaf, MapPin, RotateCcw, ShieldCheck, SlidersHorizontal, Sprout, Sun, Thermometer, Waves, Wheat } from 'lucide-react';
import { messages, type Messages } from '../lib/messages';
import { useLanguagePreference } from '../lib/language';
import { SiteFooter, SiteHeader } from './components/site-shell';
import { dateLabel, defaults, format, getPreviewComparison, validateInputs, windowDays, type CropOption, type FieldInputs, type Language, type Priority, type Season, type Soil } from '../lib/preview';

type View = 'field' | 'results';
const soilOptions: { value: Soil; label: string }[] = [
  { value: 'clayloam', label: 'Maligaya clay loam' }, { value: 'clay', label: 'Maligaya clay' },
  { value: 'siltloam', label: 'Quingua silt loam' }, { value: 'sandyloam', label: 'San Manuel sandy loam' },
];

function Choice<T extends string>({ value, options, onChange, label, className = '' }: {
  value: T; options: { value: T; label: string; icon?: React.ReactNode; hint?: string }[];
  onChange: (value: T) => void; label: string; className?: string;
}) {
  return <div className={`choices ${className}`} role="group" aria-label={label}>
    {options.map(option => <button type="button" key={option.value} aria-pressed={value === option.value} onClick={() => onChange(option.value)}>
      {option.icon}<span>{option.label}{option.hint && <small>{option.hint}</small>}</span><span className="choice-check" aria-hidden="true">{value === option.value && <Check size={13}/>}</span>
    </button>)}
  </div>;
}

function CropCard({ option, days, language, m, water, season, detailed }: { option: CropOption; days: number; language: Language; m: Messages; water: FieldInputs['water']; season: Season; detailed: boolean }) {
  const { crop, fit, blocked, conditions } = option;
  const detailsRef = useRef<HTMLDetailsElement>(null);
  useEffect(() => { if (detailsRef.current) detailsRef.current.open = detailed; }, [detailed, blocked]);
  const icon = crop.id === 'rice' ? <Wheat/> : crop.id === 'mung' ? <Sprout/> : crop.id === 'egg' ? <Leaf/> : <Sun/>;
  const used = Math.min(100, crop.days / days * 100);
  return <article className={`crop-card ${fit === 'out' ? 'crop-excluded' : ''}`} data-crop={crop.id}>
    <div className="crop-top"><span className={`crop-icon crop-${crop.id}`}>{icon}</span><span className={`fit fit-${fit}`}><span/>{m.fit[fit]}</span></div>
    <div className="crop-title"><div><h3>{language === 'en' ? crop.en : crop.tl}</h3><span>{language === 'en' ? crop.tl : crop.en}</span></div>{crop.baseline && <span className="baseline"><Wheat size={12}/>{m.baseline}</span>}</div>
    {blocked ? <div className="exclusion"><Info size={18}/><p>{blocked === 'pond' ? m.x_pond : m.x_days}</p></div> : <>
      <div className="crop-history"><span className="micro-label">{m.sampleHistory}</span><p>{format(m.hist, { a: option.history[0], b: option.history[1], s: m.hs[season] })}</p></div>
      <div className="crop-time"><span><CalendarDays size={15}/><strong>{crop.days}</strong> {m.daysUnit}</span><span>{format(m.remaining, { n: days - crop.days })}</span></div>
      <div className="duration-track" role="img" aria-label={format(m.days, { d: crop.days, n: days })}><span style={{ width: `${used}%` }}/></div>
      <details ref={detailsRef} className="crop-details"><summary>{m.more}<ChevronDown size={16}/></summary><div className="details-body">
        {option.checkDrainage && <p className="drainage-warning"><Info size={16}/>{m.x_pond_unsure}</p>}
        <h4>{m.why}</h4>
        {(['temp', 'rain', 'moist', 'tex', 'ph', 'time'] as const).filter(key => conditions[key] !== undefined).map(key => {
          const value = conditions[key]!;
          const rate = value >= .7 ? 'g' : value >= .45 ? 'o' : 'p';
          return <div className="condition-row" key={key}><span>{m.c[key]}{water === 'irrig' && (key === 'rain' || key === 'moist') && <small> · {m.irrig}</small>}</span><strong className={`rate-${rate}`}>{m.r[rate]}</strong></div>;
        })}
        <h4>{m.soilgood}</h4><p>{crop.benefit[language]}</p>
        <h4>{m.cant}</h4><ul>{option.missing.map(key => <li key={key}>{m.miss[key]}</li>)}</ul>
        <h4>{m.ask}</h4><ul>{m.asks.map(question => <li key={question}>{question}</li>)}</ul>
      </div></details>
    </>}
  </article>;
}

export default function Home() {
  const { language, setLanguage, ready } = useLanguagePreference();
  const [view, setView] = useState<View>('field');
  const [inputs, setInputs] = useState<FieldInputs>({ ...defaults });
  const [applied, setApplied] = useState<FieldInputs>({ ...defaults });
  const [season, setSeason] = useState<Season>('typical');
  const [priority, setPriority] = useState<Priority>('even');
  const [detailed, setDetailed] = useState(false);
  const [error, setError] = useState<ReturnType<typeof validateInputs>>(null);
  const [toast, setToast] = useState(false);
  const resultsHeading = useRef<HTMLHeadingElement>(null);
  const formHeading = useRef<HTMLHeadingElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const m = messages(language);
  const days = windowDays(inputs);
  const comparison = getPreviewComparison(applied, season, priority);

  useEffect(() => { if (toast) { const timer = setTimeout(() => setToast(false), 4000); return () => clearTimeout(timer); } }, [toast]);

  function update<K extends keyof FieldInputs>(key: K, value: FieldInputs[K]) { setInputs(old => ({ ...old, [key]: value })); setError(null); }
  function showForm() {
    setView('field');
    setTimeout(() => { document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); formHeading.current?.focus({ preventScroll: true }); }, 30);
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    const invalid = validateInputs(inputs); setError(invalid);
    if (invalid) { setTimeout(() => errorRef.current?.focus(), 0); return; }
    setApplied({ ...inputs }); setView('results');
    setTimeout(() => { document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth' }); resultsHeading.current?.focus({ preventScroll: true }); }, 30);
  }
  function download() {
    const blob = new Blob([JSON.stringify({ ...comparison, disclaimer: m.sampleNote }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
    anchor.href = url; anchor.download = 'aninow-sample-comparison.json'; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); setToast(true);
  }

  return <div id="top" className="app-shell">
    <a className="skip-link" href="#planner">{m.navPlan}</a>
    <SiteHeader language={language} ready={ready} onLanguageChange={setLanguage} onPlan={showForm}/>

    <main>
      <section className="landscape-hero" aria-labelledby="hero-title">
        <div className="hero-copy"><span className="scene-kicker"><span className="lime-dot"/>{m.kicker}</span><h1 id="hero-title">{language === 'en' ? <>What can you plant <em>after rice?</em></> : <>Ano ang puwedeng itanim <em>pagkatapos ng palay?</em></>}</h1><p>{m.heroCopy}</p><button className="button lime" onClick={showForm}>{m.start}<ArrowUpRight size={19}/></button></div>
        <div className="hero-visual">
          <img className="landscape-image" src="/images/farm-diorama.png" alt="" fetchPriority="high" width={1536} height={1024}/>
          <div className="hero-location"><MapPin size={15}/><span>Muñoz, Nueva Ecija<small>{m.pilot}</small></span></div>
          <div className="field-panel"><div className="field-panel-heading"><Sprout size={22}/><ArrowUpRight size={17}/></div><h2>{m.fieldCard}</h2><p>{m.fieldCopy}</p><div className="field-metrics"><div><strong>04</strong><span>{m.cropOptions}</span></div><div><strong>02</strong><span>{m.languages}</span></div></div><div className="field-panel-foot"><span className="lime-dot"/>{m.preview}<span className="artwork-label">{m.artwork}</span></div></div>
        </div>
        <div className="hero-footer"><span><Leaf size={15}/>{m.tagline}</span><a href="#planner" onClick={event => { event.preventDefault(); showForm(); }}>{m.explore}<ArrowDown size={16}/></a></div>
      </section>

      <section className="planner-section" id="planner" aria-labelledby="planner-title">
        <div className="section-navigation"><div className="steps"><span className={view === 'field' ? 'active' : 'complete'}><b>{view === 'results' ? <Check size={14}/> : '01'}</b>{m.stepOne}</span><i/><span className={view === 'results' ? 'active' : ''}><b>02</b>{m.stepTwo}</span></div><span className="preview-label"><span/>{m.preview}</span></div>

        {view === 'field' ? <>
          <div className="section-heading"><div><span className="eyebrow">{m.formKicker}</span><h2 id="planner-title" tabIndex={-1} ref={formHeading}>{m.formIntro}</h2><p>{m.formCopy}</p></div><Sprout className="heading-sprout" size={45} strokeWidth={1}/></div>
          <div className="form-layout"><form onSubmit={submit} noValidate aria-busy={!ready}><fieldset className="interactive-fields" disabled={!ready}>
            {error && <div className="form-error" role="alert" tabIndex={-1} ref={errorRef}><Info size={19}/><div><strong>{m.validationTitle}</strong><p>{error === 'dates' ? m.errorDates : error === 'order' ? m.errorOrder : m.errorPh}</p></div></div>}
            <div className="form-card"><div className="card-heading"><span className="section-icon"><Earth size={21}/></span><div><h3>{m.fieldHeading}</h3><p>{m.fieldSub}</p></div><span className="card-number">01</span></div>
              <div className="two-columns"><div className="field"><label htmlFor="location">{m.f_place}</label><div className="select-wrap"><MapPin size={16}/><select id="location" disabled aria-describedby="pilot-hint"><option>Muñoz, Nueva Ecija</option></select><ChevronDown size={15}/></div><p className="field-hint" id="pilot-hint">{m.pilotOnly}</p></div><div className="field"><label htmlFor="soil">{m.f_soil}</label><div className="select-wrap"><select id="soil" value={inputs.soil} onChange={event => update('soil', event.target.value as Soil)}>{soilOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}<option value="">{m.dontknow}</option></select><ChevronDown size={15}/></div></div></div>
              <fieldset><legend>{m.f_pond}</legend><Choice value={inputs.pond} label={m.f_pond} onChange={value => update('pond', value)} options={[{ value: 'no', label: m.no }, { value: 'yes', label: m.yes }, { value: 'unsure', label: m.unsure }]}/></fieldset>
              <fieldset><legend>{m.f_water}</legend><Choice value={inputs.water} label={m.f_water} onChange={value => update('water', value)} options={[{ value: 'rain', label: m.w_rain, icon: <CloudRain size={19}/> }, { value: 'irrig', label: m.w_irrig, icon: <Waves size={19}/> }]}/></fieldset>
            </div>
            <div className="form-card"><div className="card-heading"><span className="section-icon"><CalendarDays size={21}/></span><div><h3>{m.calendarHeading}</h3><p>{m.calendarSub}</p></div><span className="card-number">02</span></div>
              <div className="two-columns"><div className="field"><label htmlFor="harvest">{m.f_harvest}</label><input required type="date" id="harvest" value={inputs.harvest} aria-invalid={error === 'dates' || error === 'order'} onChange={event => update('harvest', event.target.value)}/></div><div className="field"><label htmlFor="next">{m.f_next}</label><input required type="date" id="next" value={inputs.next} aria-invalid={error === 'dates' || error === 'order'} onChange={event => update('next', event.target.value)}/></div></div>
              <div className="field ph-field"><label htmlFor="ph">{m.f_ph}<span>{m.optional}</span></label><input id="ph" type="number" min="3" max="10" step="0.1" inputMode="decimal" placeholder="—" value={inputs.ph} onChange={event => update('ph', event.target.value)} aria-invalid={error === 'ph'} aria-describedby="ph-hint"/><p id="ph-hint" className="field-hint">{m.f_ph_hint}</p></div>
            </div>
            <div className="form-actions"><p><ShieldCheck size={17}/>{m.savedLocally}</p><button className="button primary" type="submit">{m.go}<ArrowRight size={19}/></button></div>
          </fieldset></form>
          <aside className="planner-aside"><div className="window-card"><div className="window-top"><CalendarDays size={20}/><span className="micro-label">{m.windowLabel}</span></div><div className="window-value"><strong>{days > 0 ? days : '—'}</strong><span>{m.available}</span></div><div className="season-lines" aria-hidden="true"><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/></div><div className="window-dates"><div><span className="timeline-dot"/><div><small>{m.riceHarvest}</small><strong>{dateLabel(inputs.harvest, language)}</strong></div></div><i/><div><span className="timeline-dot end"/><div><small>{m.nextPlanting}</small><strong>{dateLabel(inputs.next, language)}</strong></div></div></div><p>{days > 0 ? m.calendarNote : m.nothingYet}</p></div><div className="aside-note"><CircleHelp size={21}/><p>{m.formNote}</p></div><div className="sample-notice"><Info size={17}/><p>{m.notice}</p></div></aside></div>
        </> : <>
          <div className="section-heading results-heading"><div><span className="eyebrow">{m.resultsKicker}</span><h2 id="planner-title" tabIndex={-1} ref={resultsHeading}>{m.r_title}</h2><p>{m.resultsIntro}</p></div><button className="button secondary" onClick={showForm}><ArrowLeft size={16}/>{m.edit}</button></div>
          <div className="result-window"><span className="result-window-icon"><CalendarDays size={24}/></span><div><h3>{format(m.win, { n: comparison.days })}</h3><p>{dateLabel(applied.harvest, language)} <ArrowRight size={13}/> {dateLabel(applied.next, language)}<span>·</span><MapPin size={13}/> Muñoz, Nueva Ecija</p></div><span className="window-leaf"><Sprout size={65} strokeWidth={.8}/></span></div>
          <div className="results-notice"><Info size={18}/><p><strong>{m.sampleLabel}.</strong> {m.sampleNote}</p></div>
          <div className="detail-toolbar"><p id="detail-hint">{m.detailHint}</p><div className="detail-switch" role="group" aria-label={m.resultView} aria-describedby="detail-hint"><button type="button" aria-pressed={!detailed} onClick={() => setDetailed(false)}>{m.simpleView}</button><button type="button" aria-pressed={detailed} onClick={() => setDetailed(true)}>{m.moreDetailed}</button></div></div>
          <div className="results-layout"><aside className="filter-card"><div className="filter-heading"><SlidersHorizontal size={20}/><h3>{m.filtersTitle}</h3></div><p>{m.filtersHint}</p><fieldset><legend>{m.season}</legend><Choice className="vertical" value={season} onChange={setSeason} label={m.season} options={[
            { value: 'typical', label: m.s_typical, icon: <Sun size={18}/> }, { value: 'dry', label: m.s_dry, icon: <Thermometer size={18}/> }, { value: 'nino', label: m.s_nino, icon: <CloudRain size={18}/> },
          ]}/></fieldset><fieldset><legend>{m.priority}</legend><Choice className="vertical" value={priority} onChange={setPriority} label={m.priority} options={[
            { value: 'even', label: m.p_even, icon: <SlidersHorizontal size={18}/> }, { value: 'water', label: m.p_water, icon: <Droplets size={18}/> }, { value: 'soil', label: m.p_soil, icon: <Leaf size={18}/> }, { value: 'time', label: m.p_time, icon: <CalendarDays size={18}/> },
          ]}/></fieldset></aside><div className="crop-area"><div className="crop-area-heading"><h3>{format(m.compareCount, { n: comparison.options.length })}</h3><span>{m.sampleOrder}</span></div><div className="crop-grid">{comparison.options.map(option => <CropCard key={option.crop.id} option={option} days={comparison.days} language={language} m={m} water={applied.water} season={season} detailed={detailed}/>)}</div></div></div>
          <div className="results-actions"><button className="text-button" onClick={() => { setInputs({ ...defaults }); setApplied({ ...defaults }); setSeason('typical'); setPriority('even'); setDetailed(false); setError(null); showForm(); }}><RotateCcw size={16}/>{m.reset}</button><button className="button secondary" onClick={download}><Download size={17}/>{m.download}</button></div>
        </>}
      </section>

      <section className="about-section" id="about" aria-labelledby="about-title"><div className="about-intro"><span className="eyebrow"><Leaf size={15}/>{m.aboutKicker}</span><h2 id="about-title">{m.sourceTitle}</h2><p>{m.sourceCopy}</p></div><div className="about-grid">{[{ icon: <Earth/>, title: m.sourceOne, copy: m.sourceOneCopy }, { icon: <CloudRain/>, title: m.sourceTwo, copy: m.sourceTwoCopy }, { icon: <Sprout/>, title: m.sourceThree, copy: m.sourceThreeCopy }].map((item, index) => <div className="about-card" key={item.title}><div>{item.icon}<span>0{index + 1}</span></div><h3>{item.title}</h3><p>{item.copy}</p></div>)}</div><p className="source-note"><Info size={16}/>{m.sourceFoot}</p></section>
    </main>
    <SiteFooter language={language}/>
    {toast && <div className="toast" role="status"><Check size={18}/>{m.downloaded}</div>}
  </div>;
}
