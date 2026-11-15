'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, CalendarDays, Check, ChevronDown, CircleHelp, CloudRain, Download, Droplets, Earth, Info, Leaf, MapPin, RotateCcw, ShieldCheck, SlidersHorizontal, Sprout, Sun, Thermometer, Waves, Wheat } from 'lucide-react';
import { messages, type Messages } from '../lib/messages';
import { useLanguagePreference } from '../lib/language';
import { SiteFooter, SiteHeader } from './components/site-shell';
import { AppIntro } from './components/app-intro';
import { compare, cropOptions, dateLabel, defaults, format, getCatalog, ModelError, validateInputs, windowDays, type Catalog, type Comparison, type FieldInputs, type Language, type Priority, type Season } from '../lib/model';

type View = 'field' | 'results';

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

function CropCard({ option, days, language, m, mainCrop, season, detailed, comparison }: {
  option: ReturnType<typeof cropOptions>[number]; days: number; language: Language; m: Messages;
  mainCrop: string; season: Season; detailed: boolean; comparison: Comparison;
}) {
  const { crop, result, excluded } = option;
  const scores = result?.median_scores.short;
  const values = scores ? Object.values(scores).filter((value): value is number => value !== null) : [];
  // Same display bands as model/serve.py; no suitability is calculated here.
  const weakest = values.length ? Math.min(...values) : null;
  const fit = excluded.length ? 'out' : weakest === null ? null : weakest >= .7 ? 'good' : weakest >= .45 ? 'ok' : 'poor';
  const detailsRef = useRef<HTMLDetailsElement>(null);
  useEffect(() => { if (detailsRef.current) detailsRef.current.open = detailed; }, [detailed]);
  const icon = crop.id === 'rice' ? <Wheat/> : <Sprout/>;
  const duration = result?.scored_days.short;
  const history = result?.counts.balanced[season].short;
  const gap = result?.median_deficit_mm.short;
  return <article className={`crop-card ${fit === 'out' ? 'crop-excluded' : ''}`} data-crop={crop.id}>
    <div className="crop-top"><span className={`crop-icon crop-${crop.id}`}>{icon}</span><span className={`fit fit-${fit ?? 'ok'}`}><span/>{fit ? m.fit[fit] : m.unknown}</span></div>
    <div className="crop-title"><div><h3>{language === 'en' ? crop.name : crop.local_name}</h3><span>{language === 'en' ? crop.local_name : crop.name}</span></div>{crop.id === mainCrop && <span className="baseline"><Wheat size={12}/>{m.baseline}</span>}</div>
    {excluded.length ? <div className="exclusion"><Info size={18}/><div>{excluded.map(reason => <p key={reason}>{m.reasons[reason as keyof typeof m.reasons] ?? m.excluded}</p>)}</div></div> : result && <>
      <div className="crop-history"><span className="micro-label">{m.historyLabel}</span><p>{history && history.of > 0 ? format(m.hist, { a: history.pass, b: history.of, s: m.hs[season] }) : m.noHistory}</p></div>
      <div className="crop-time"><span><CalendarDays size={15}/><strong>{duration}{result.scored_days.long !== duration ? `–${result.scored_days.long}` : ''}</strong> {m.daysUnit}</span><span>{format(m.remaining, { n: days - duration! - comparison.inputs.turnaround_days })}</span></div>
      <div className="duration-track" role="img" aria-label={format(m.days, { d: duration!, n: days })}><span style={{ width: `${Math.min(100, duration! / days * 100)}%` }}/></div>
      <p className="model-fact">{m.gap}: <strong>{gap == null ? m.unknown : `${new Intl.NumberFormat(language === 'tl' ? 'fil-PH' : 'en-PH', { maximumFractionDigits: 0 }).format(gap)} mm`}</strong></p>
      <details ref={detailsRef} className="crop-details"><summary>{m.more}<ChevronDown size={16}/></summary><div className="details-body">
        {result.flags.includes('drainage_unconfirmed') && result.drainage_requirement.startsWith('well') && <p className="drainage-warning"><Info size={16}/>{m.drainageNote}</p>}
        <h4>{m.why}</h4>
        {(['temp', 'water', 'ph', 'texture'] as const).map(key => {
          const value = scores![key];
          return <div className="condition-row" key={key}><span>{m.conditions[key]}</span><strong>{value === null ? m.notScored : value.toFixed(2)}</strong></div>;
        })}
        <p>{m.historicalNote}</p>
        {history && <><p>{format(m.omitted, { n: history.not_scored })}</p>{history.wilson95[0] !== null && history.wilson95[1] !== null && <p>{format(m.interval, { lo: Math.round(history.wilson95[0] * 100), hi: Math.round(history.wilson95[1] * 100) })} — {m.historyNote}</p>}</>}
        <h4>{m.sources}</h4><p>{result.limits_source}</p><p>{result.cycle_source}</p><h4>{m.waterSource}</h4><p>{comparison.results.crop_coefficients[crop.id]?.source ?? m.unknown}</p>
        <h4>{m.cant}</h4><p>{m.modelLimits}</p>
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
  const [season, setSeason] = useState<Season>('all');
  const [priority, setPriority] = useState<Priority>('balanced');
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [pending, setPending] = useState(false);
  const [serviceError, setServiceError] = useState<ModelError | null>(null);
  const requestRef = useRef<AbortController | null>(null);
  const [soilTest, setSoilTest] = useState(false);
  const [detailed, setDetailed] = useState(false);
  const [error, setError] = useState<ReturnType<typeof validateInputs>>(null);
  const [toast, setToast] = useState(false);
  const resultsHeading = useRef<HTMLHeadingElement>(null);
  const formHeading = useRef<HTMLHeadingElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const m = messages(language);
  const days = windowDays(inputs);
  const options = comparison && catalog ? cropOptions(comparison, catalog, priority) : [];

  useEffect(() => {
    const controller = new AbortController();
    setLoadingCatalog(true); setServiceError(null);
    getCatalog(controller.signal).then(value => { if (!controller.signal.aborted) setCatalog(value); })
      .catch(error => { if (!controller.signal.aborted) setServiceError(error instanceof ModelError ? error : new ModelError('network')); })
      .finally(() => { if (!controller.signal.aborted) setLoadingCatalog(false); });
    return () => controller.abort();
  }, [catalogAttempt]);
  useEffect(() => () => requestRef.current?.abort(), []);

  useEffect(() => { if (toast) { const timer = setTimeout(() => setToast(false), 4000); return () => clearTimeout(timer); } }, [toast]);

  function update<K extends keyof FieldInputs>(key: K, value: FieldInputs[K]) { setInputs(old => ({ ...old, [key]: value })); setError(null); if (catalog) setServiceError(null); }
  function showForm() {
    setView('field');
    setTimeout(() => { document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); formHeading.current?.focus({ preventScroll: true }); }, 30);
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    const invalid = validateInputs(inputs); setError(invalid);
    if (invalid) { setTimeout(() => errorRef.current?.focus(), 0); return; }
    if (!catalog || pending) return;
    const controller = new AbortController(); requestRef.current = controller;
    setPending(true); setServiceError(null);
    try {
      const result = await compare(inputs, priority, controller.signal);
      for (const key of ['balanced', 'saving_water', 'healthier_soil', 'finishing_early'] as const) cropOptions(result, catalog, key);
      setComparison(result); setApplied({ ...inputs }); setView('results');
      setTimeout(() => { document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth' }); resultsHeading.current?.focus({ preventScroll: true }); }, 30);
    } catch (error) {
      if (!controller.signal.aborted) { setServiceError(error instanceof ModelError ? error : new ModelError('network')); setTimeout(() => errorRef.current?.focus(), 0); }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }
  function download() {
    if (!comparison) return;
    const blob = new Blob([JSON.stringify({ ...comparison, display: { season, priority }, disclaimer: m.modelLimits }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
    anchor.href = url; anchor.download = 'aninow-model-comparison.json'; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); setToast(true);
  }

  return <AppIntro language={language}><div id="top" className="app-shell planner-shell">
    <a className="skip-link" href="#planner">{m.navPlan}</a>
    <SiteHeader language={language} ready={ready} onLanguageChange={setLanguage} onPlan={showForm}/>

    <main>
      <section className="planner-intro" aria-labelledby="hero-title">
        <h1 id="hero-title">{m.heroTitle} <em>{m.heroEmphasis}</em></h1>
        <p>{m.heroCopy}</p>
      </section>

      <section className="planner-section" id="planner" aria-labelledby="planner-title">
        <div className="section-navigation"><div className="steps"><span className={view === 'field' ? 'active' : 'complete'}><b>{view === 'results' ? <Check size={14}/> : '01'}</b>{m.stepOne}</span><i/><span className={view === 'results' ? 'active' : ''}><b>02</b>{m.stepTwo}</span></div><span className="model-label"><span/>{m.modelLabel}</span></div>

        {view === 'field' || !comparison ? <>
          <h2 id="planner-title" className="sr-only" tabIndex={-1} ref={formHeading}>{m.stepOne}</h2>
          {(loadingCatalog || pending) && <p className="model-status" role="status">{pending ? m.calculating : m.loadingCatalog}</p>}
          {serviceError && <div className="form-error" role="alert" tabIndex={-1} ref={errorRef}><Info size={19}/><div><strong>{m.errors[serviceError.kind]}</strong>{serviceError.requestId && <small>{serviceError.requestId}</small>}{serviceError.kind === 'validation' && <ul>{Object.entries(serviceError.fields).map(([field, messages]) => <li key={field}>{field}: {messages.join(' ')}</li>)}</ul>}{!catalog && <button type="button" className="button secondary" onClick={() => setCatalogAttempt(value => value + 1)}>{m.retry}</button>}</div></div>}
          <div className="form-layout"><form onSubmit={submit} noValidate aria-busy={!ready || pending || loadingCatalog}><fieldset className="interactive-fields" disabled={!ready || pending || loadingCatalog}>
            {error && <div className="form-error" role="alert" tabIndex={-1} ref={errorRef}><Info size={19}/><div><strong>{m.validationTitle}</strong><p>{m.errors[error]}</p></div></div>}
            <div className="form-card"><div className="card-heading"><span className="section-icon"><Earth size={21}/></span><div><h3>{m.fieldHeading}</h3><p>{m.fieldSub}</p></div><span className="card-number">01</span></div>
              <div className="two-columns"><div className="field"><label htmlFor="location">{m.f_place}</label><div className="select-wrap"><MapPin size={16}/><select id="location" value={inputs.place} onChange={event => update('place', event.target.value)} aria-describedby="pilot-hint">{catalog?.places.map(place => <option key={place.id} value={place.id}>{place.name}, {place.province}</option>)}</select><ChevronDown size={15}/></div><p className="field-hint" id="pilot-hint">{m.pilotOnly}</p></div><div className="field"><label htmlFor="main-crop">{m.mainCrop}</label><div className="select-wrap"><select id="main-crop" value={inputs.main_crop} onChange={event => update('main_crop', event.target.value)}>{catalog?.crops.map(crop => <option key={crop.id} value={crop.id}>{language === 'en' ? crop.name : crop.local_name}</option>)}</select><ChevronDown size={15}/></div></div></div>
              <fieldset aria-describedby="drainage-hint"><legend>{m.f_pond}</legend><Choice value={inputs.drainage} label={m.f_pond} onChange={value => update('drainage', value)} options={[{ value: 'well_drained', label: m.no }, { value: 'poorly_drained', label: m.yes }, { value: 'unknown', label: m.unsure }]}/><p className="field-hint" id="drainage-hint">{m.drainageHint}</p></fieldset>
              <fieldset><legend>{m.f_water}</legend><Choice value={inputs.water} label={m.f_water} onChange={value => update('water', value)} options={[{ value: 'rain', label: m.w_rain, icon: <CloudRain size={19}/> }, { value: 'irrigation', label: m.w_irrig, icon: <Waves size={19}/> }]}/></fieldset>
              {inputs.water === 'irrigation' && inputs.drainage === 'poorly_drained' && <p className="field-hint">{m.irrigationDrainageNote}</p>}
            </div>
            <div className="form-card"><div className="card-heading"><span className="section-icon"><CalendarDays size={21}/></span><div><h3>{m.calendarHeading}</h3><p>{m.calendarSub}</p></div><span className="card-number">02</span></div>
              <div className="two-columns"><div className="field"><label htmlFor="harvest">{m.f_harvest}</label><input required type="date" id="harvest" value={inputs.harvest} aria-invalid={error === 'dates' || error === 'order'} onChange={event => update('harvest', event.target.value)}/></div><div className="field"><label htmlFor="next">{m.f_next}</label><input required type="date" id="next" value={inputs.next_planting} aria-invalid={error === 'dates' || error === 'order'} onChange={event => update('next_planting', event.target.value)}/></div></div>
            </div>
            <div className="form-card"><label className="soil-toggle"><input type="checkbox" checked={soilTest} onChange={event => { setSoilTest(event.target.checked); if (!event.target.checked) { update('soil_ph', ''); update('soil_texture', ''); } }}/>{m.soilTest}</label><p className="field-hint">{m.soilHint}</p>{soilTest && <div className="two-columns"><div className="field"><label htmlFor="ph">{m.f_ph}</label><input id="ph" type="number" min="3" max="10" step="any" inputMode="decimal" value={inputs.soil_ph} onChange={event => update('soil_ph', event.target.value)} aria-invalid={error === 'ph'}/></div><div className="field"><label htmlFor="soil-texture">{m.soilTexture}</label><select id="soil-texture" value={inputs.soil_texture} onChange={event => update('soil_texture', event.target.value as FieldInputs['soil_texture'])}><option value="">{m.dontknow}</option>{(['light', 'medium', 'heavy'] as const).map(value => <option key={value} value={value}>{m.texture[value]}</option>)}</select></div></div>}</div>
            <details className="form-card model-settings"><summary>{m.advanced}<ChevronDown size={16}/></summary><div className="two-columns"><div className="field"><label htmlFor="pass-mark">{m.passMark}</label><input id="pass-mark" type="number" min="0" max="1" step="any" value={inputs.pass_mark} onChange={event => update('pass_mark', event.target.value)} aria-describedby="pass-hint"/><p className="field-hint" id="pass-hint">{m.passHint}</p></div><div className="field"><label htmlFor="preparation">{m.preparation}</label><input id="preparation" type="number" min="0" max="90" step="1" value={inputs.turnaround_days} onChange={event => update('turnaround_days', event.target.value)} aria-describedby="prep-hint"/><p className="field-hint" id="prep-hint">{m.prepHint}</p></div></div></details>
            <div className="form-card"><fieldset><legend>{m.priority}</legend><Choice value={priority} onChange={setPriority} label={m.priority} options={[{ value: 'balanced', label: m.p_even }, { value: 'saving_water', label: m.p_water }, { value: 'healthier_soil', label: m.p_soil }, { value: 'finishing_early', label: m.p_time }]}/></fieldset></div>
            <div className="form-actions"><p><ShieldCheck size={17}/>{m.savedLocally}</p><button className="button primary" type="submit" disabled={!catalog || pending || loadingCatalog}>{serviceError ? m.retry : m.go}<ArrowRight size={19}/></button></div>
          </fieldset></form>
          <aside className="planner-aside"><div className="window-card"><div className="window-top"><CalendarDays size={20}/><span className="micro-label">{m.windowLabel}</span></div><div className="window-value"><strong>{days > 0 ? days : '—'}</strong><span>{m.available}</span></div><div className="season-lines" aria-hidden="true"><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/></div><div className="window-dates"><div><span className="timeline-dot"/><div><small>{m.riceHarvest}</small><strong>{dateLabel(inputs.harvest, language)}</strong></div></div><i/><div><span className="timeline-dot end"/><div><small>{m.nextPlanting}</small><strong>{dateLabel(inputs.next_planting, language)}</strong></div></div></div><p>{days > 0 ? m.calendarNote : m.nothingYet}</p></div><div className="aside-note"><CircleHelp size={21}/><p>{m.formNote}</p></div><div className="field-notice"><Info size={17}/><p>{m.notice}</p></div></aside></div>
        </> : <>
          <div className="section-heading results-heading"><div><span className="eyebrow">{m.resultsKicker}</span><h2 id="planner-title" tabIndex={-1} ref={resultsHeading}>{m.r_title}</h2><p>{m.resultsIntro}</p></div><button className="button secondary" onClick={showForm}><ArrowLeft size={16}/>{m.edit}</button></div>
          <div className="result-window"><span className="result-window-icon"><CalendarDays size={24}/></span><div><h3>{format(m.win, { n: comparison.results.meta.window_days })}</h3><p>{dateLabel(applied.harvest, language)} <ArrowRight size={13}/> {dateLabel(applied.next_planting, language)}<span>·</span><MapPin size={13}/> {applied.place}</p></div><span className="window-leaf"><Sprout size={65} strokeWidth={.8}/></span></div>
          <div className="results-notice"><Info size={18}/><p><strong>{m.resultsLabel}.</strong> {m.modelLimits}</p></div>
          <div className="model-context">
            <p>{m.waterSupply}: <strong>{comparison.inputs.water === 'irrigation' ? m.w_irrig : m.w_rain}</strong> · {m.drainageLabel}: <strong>{m.drainageAnswers[comparison.inputs.drainage]}</strong></p>
            {comparison.inputs.water === 'irrigation' && comparison.inputs.drainage === 'poorly_drained' && <p>{m.irrigationDrainageNote}</p>}
            <p>{m.soilUsed}: {comparison.results.soil.ph ?? m.unknown} pH · {comparison.results.soil.texture ? m.texture[comparison.results.soil.texture as keyof typeof m.texture] ?? m.unknown : m.unknown}</p><p>{m.f_ph}: {comparison.inputs.soil_ph === null ? m.nearbySample : m.measured} · {m.soilTexture}: {comparison.inputs.soil_texture === null ? m.nearbySample : m.measured}</p><p>{comparison.results.soil.source}</p><p>{m.passMark}: {comparison.inputs.pass_mark} · {m.preparation}: {comparison.inputs.turnaround_days}</p><p>{m.historicalNote}</p>{comparison.inputs.water === 'irrigation' && <p>{m.irrigationNote}</p>}{comparison.inputs.drainage === 'unknown' && <p>{m.drainageNote}</p>}<p>{m.reviewNote}</p>
          </div>
          <div className="detail-toolbar"><p id="detail-hint">{m.detailHint}</p><div className="detail-switch" role="group" aria-label={m.resultView} aria-describedby="detail-hint"><button type="button" aria-pressed={!detailed} onClick={() => setDetailed(false)}>{m.simpleView}</button><button type="button" aria-pressed={detailed} onClick={() => setDetailed(true)}>{m.moreDetailed}</button></div></div>
          <div className="results-layout"><aside className="filter-card"><div className="filter-heading"><SlidersHorizontal size={20}/><h3>{m.filtersTitle}</h3></div><p>{m.filtersHint}</p><fieldset><legend>{m.season}</legend><Choice className="vertical" value={season} onChange={setSeason} label={m.season} options={[
            { value: 'all', label: m.allSeasons, icon: <Earth size={18}/> }, { value: 'normal', label: m.s_typical, icon: <Sun size={18}/> }, { value: 'dry', label: m.s_dry, icon: <Thermometer size={18}/> }, { value: 'el_nino', label: m.s_nino, icon: <CloudRain size={18}/> },
          ]}/></fieldset><fieldset><legend>{m.priority}</legend><Choice className="vertical" value={priority} onChange={setPriority} label={m.priority} options={[
            { value: 'balanced', label: m.p_even, icon: <SlidersHorizontal size={18}/> }, { value: 'saving_water', label: m.p_water, icon: <Droplets size={18}/> }, { value: 'healthier_soil', label: m.p_soil, icon: <Leaf size={18}/> }, { value: 'finishing_early', label: m.p_time, icon: <CalendarDays size={18}/> },
          ]}/></fieldset></aside><div className="crop-area"><div className="crop-area-heading"><h3>{format(m.compareCount, { n: options.length })}</h3><span>{m.modelOrder}</span></div><div className="crop-grid">{options.map(option => <CropCard key={option.crop.id} option={option} days={comparison.results.meta.window_days} language={language} m={m} mainCrop={applied.main_crop} season={season} detailed={detailed} comparison={comparison}/>)}</div></div></div>
          <div className="results-actions"><button className="text-button" onClick={() => { setInputs({ ...defaults }); setApplied({ ...defaults }); setSeason('all'); setPriority('balanced'); setComparison(null); setSoilTest(false); setServiceError(null); setDetailed(false); setError(null); showForm(); }}><RotateCcw size={16}/>{m.reset}</button><button className="button secondary" onClick={download}><Download size={17}/>{m.download}</button></div>
        </>}
      </section>

      <section className="about-section" id="about" aria-labelledby="about-title"><div className="about-intro"><span className="eyebrow"><Leaf size={15}/>{m.aboutKicker}</span><h2 id="about-title">{m.sourceTitle}</h2><p>{m.sourceCopy}</p></div><div className="about-grid">{[{ icon: <Earth/>, title: m.sourceOne, copy: m.sourceOneCopy }, { icon: <CloudRain/>, title: m.sourceTwo, copy: m.sourceTwoCopy }, { icon: <Sprout/>, title: m.sourceThree, copy: m.sourceThreeCopy }].map((item, index) => <div className="about-card" key={item.title}><div>{item.icon}<span>0{index + 1}</span></div><h3>{item.title}</h3><p>{item.copy}</p></div>)}</div><p className="source-note"><Info size={16}/>{m.sourceFoot}</p></section>
    </main>
    <SiteFooter language={language}/>
    {toast && <div className="toast" role="status"><Check size={18}/>{m.downloaded}</div>}
  </div></AppIntro>;
}
