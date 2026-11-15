'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, CalendarDays, Check, ChevronDown, CircleHelp, CloudRain, Download, Droplets, Earth, Info, Leaf, MapPin, RotateCcw, ShieldCheck, SlidersHorizontal, Sun, Thermometer, Waves, Wheat } from 'lucide-react';
import { messages, type Messages } from '../lib/messages';
import { useLanguagePreference } from '../lib/language';
import { SiteFooter, SiteHeader } from './components/site-shell';
import { AppIntro } from './components/app-intro';
import { CalculationLoading } from './components/calculation-loading';
import { PlantingDates, RecommendationNotice, WholeSchedule } from './components/model-evidence';
import { ResultOverview } from './components/result-overview';
import { CropPhoto } from './components/crop-photo';
import { CropReferences } from './components/crop-references';
import { compare, cropFit, cropOptions, dateLabel, defaults, format, getCatalog, ModelError, validateInputs, windowDays, type Catalog, type Comparison, type FieldInputs, type Language, type Priority, type Season } from '../lib/model';

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
  const fit = cropFit(result, excluded);
  const field = comparison.results.fields[comparison.inputs.water];
  const plan = field.schedule?.[crop.id];
  const spare = plan?.spare_days ?? days - (result?.scored_days.short ?? 0) - comparison.inputs.turnaround_days;
  const total = plan?.total_days ?? result?.scored_days.short;
  const detailsRef = useRef<HTMLDetailsElement>(null);
  useEffect(() => { if (detailsRef.current) detailsRef.current.open = detailed; }, [detailed]);
  const duration = result?.scored_days.short;
  const history = result?.counts.balanced[season].short;
  const gap = result?.median_deficit_mm.short;
  const rating = result?.median_S?.short.balanced;
  return <article className={`crop-card ${fit === 'out' ? 'crop-excluded' : ''}`} data-crop={crop.id}>
    <CropPhoto cropId={crop.id} name={language === 'en' ? crop.name : crop.local_name} m={m}/>
    <div className="crop-body">
    <div className="crop-top"><div className="crop-rating"><span className={`fit fit-${fit ?? 'ok'}`}><span/>{fit === 'partial' ? m.partial : fit ? m.fit[fit] : m.unknown}</span>{rating != null && <span className="model-rating" title={m.scoreHint}><span>{m.scoreLabel}</span><strong>{rating.toFixed(2)}<span> / 1</span></strong></span>}</div></div>
    <div className="crop-title"><div><h3>{language === 'en' ? crop.name : crop.local_name}</h3><span>{language === 'en' ? crop.local_name : crop.name}</span></div>{crop.id === mainCrop && <span className="baseline"><Wheat size={12}/>{m.baseline}</span>}</div>
    {field.recommendation?.suitable.includes(crop.id) && <p className="recommendation-tag"><Check size={15}/>{m.recommended}</p>}
    {result?.not_scored?.length ? <p className="evidence-note">{format(m.partialNote, { conditions: result.not_scored.map(key => m.conditions[key]).join(', ') })}</p> : null}
    {excluded.length > 0 && plan && !plan.fits && <p className="evidence-note">{format(m.totalDays, { n: plan.total_days })} · {format(m.scheduleOver, { n: -plan.spare_days })}</p>}
    {excluded.length ? <div className="exclusion"><Info size={18}/><div>{excluded.map(reason => <p key={reason}>{m.reasons[reason as keyof typeof m.reasons] ?? m.excluded}</p>)}</div></div> : result && <>
      <div className="crop-history"><span className="micro-label">{m.historyLabel}</span><p>{history && history.of > 0 ? format(m.hist, { a: history.pass, b: history.of, s: m.hs[season] }) : m.noHistory}</p></div>
      <div className="crop-time"><span><CalendarDays size={15}/><strong>{duration}{result.scored_days.long !== duration ? `–${result.scored_days.long}` : ''}</strong> {m.daysUnit}</span><span>{spare < 0 ? format(m.scheduleOver, { n: -spare }) : format(m.remaining, { n: spare })}</span></div>
      <div className="duration-track" role="img" aria-label={`${m.schedule}: ${format(m.totalDays, { n: total! })}`}><span style={{ width: `${Math.min(100, total! / days * 100)}%` }}/></div>
      <p className="model-fact">{m.gap}: <strong>{gap == null ? m.unknown : `${new Intl.NumberFormat(language === 'tl' ? 'fil-PH' : 'en-PH', { maximumFractionDigits: 0 }).format(gap)} mm`}</strong></p>
      <details ref={detailsRef} className="crop-details"><summary>{m.more}<ChevronDown size={16}/></summary><div className="details-body">
        {result.flags.includes('drainage_unconfirmed') && result.drainage_requirement.startsWith('well') && <p className="drainage-warning"><Info size={16}/>{m.drainageNote}</p>}
        {plan && <WholeSchedule plan={plan} m={m}/>}
        {field.same_family_as_main?.includes(crop.id) && <p className="evidence-note">{m.sameFamily}{result.family ? ` (${result.family})` : ''}</p>}
        {result.guide_check?.outside && <p className="evidence-note">{format(m.guideCaution, { temp: result.guide_check.median_temp_c, lo: result.guide_check.guide_temp_c[0], hi: result.guide_check.guide_temp_c[1] })}</p>}
        <h4>{m.why}</h4><p>{m.scoreHint}</p>
        {(['temp', 'water', 'ph', 'texture'] as const).map(key => {
          const value = scores![key];
          return <div className="condition-row" key={key}><span>{m.conditions[key]}</span><strong>{value === null ? m.notScored : value.toFixed(2)}</strong></div>;
        })}
        <p>{m.historicalNote}</p>
        {history && <><p>{format(m.omitted, { n: history.not_scored })}</p>{history.wilson95[0] !== null && history.wilson95[1] !== null && <p>{format(m.interval, { lo: Math.round(history.wilson95[0] * 100), hi: Math.round(history.wilson95[1] * 100) })} — {m.historyNote}</p>}</>}
        <PlantingDates comparison={comparison} cropId={crop.id} language={language} m={m}/>
        <CropReferences result={result} waterSource={comparison.results.crop_coefficients[crop.id]?.source ?? ''} heading={m.sources} unmatchedLabel={m.sourceNote} notesLabel={m.sourceNotes}/>
        <h4>{m.cant}</h4><p>{m.modelLimits}</p>
        <h4>{m.ask}</h4><ul>{m.asks.map(question => <li key={question}>{question}</li>)}</ul>
      </div></details>
    </>}
    </div>
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
  const calculationHeading = useRef<HTMLHeadingElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const m = messages(language);
  const days = windowDays(inputs);
  const seasonLabel = { all: m.allSeasons, normal: m.s_typical, dry: m.s_dry, el_nino: m.s_nino }[season];
  const priorityLabel = { balanced: m.p_even, saving_water: m.p_water, healthier_soil: m.p_soil, finishing_early: m.p_time }[priority];
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

  useEffect(() => {
    if (pending) {
      document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      calculationHeading.current?.focus({ preventScroll: true });
    } else if (serviceError) {
      errorRef.current?.focus();
    }
  }, [pending, serviceError]);

  useEffect(() => { if (toast) { const timer = setTimeout(() => setToast(false), 4000); return () => clearTimeout(timer); } }, [toast]);

  function update<K extends keyof FieldInputs>(key: K, value: FieldInputs[K]) { setInputs(old => ({ ...old, [key]: value })); setError(null); if (catalog) setServiceError(null); }
  function showForm() {
    setView('field');
    setTimeout(() => { document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); formHeading.current?.focus({ preventScroll: true }); }, 30);
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    const invalid = validateInputs(inputs); setError(invalid);
    if (invalid) { if (['prepDays', 'pickingDays', 'preparation', 'passMark'].includes(invalid)) document.querySelector<HTMLDetailsElement>('.model-settings')?.setAttribute('open', ''); setTimeout(() => errorRef.current?.focus(), 0); return; }
    if (!catalog || pending) return;
    const controller = new AbortController(); requestRef.current = controller;
    setPending(true); setServiceError(null);
    try {
      const result = await compare(inputs, priority, controller.signal);
      for (const key of ['balanced', 'saving_water', 'healthier_soil', 'finishing_early'] as const) cropOptions(result, catalog, key);
      setComparison(result); setApplied({ ...inputs }); setView('results');
      setTimeout(() => { document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth' }); resultsHeading.current?.focus({ preventScroll: true }); }, 30);
    } catch (error) {
      if (!controller.signal.aborted) { setServiceError(error instanceof ModelError ? error : new ModelError('network')); }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }
  function reset() {
    setInputs({ ...defaults }); setApplied({ ...defaults }); setSeason('all'); setPriority('balanced');
    setComparison(null); setSoilTest(false); setServiceError(null); setDetailed(false); setError(null); showForm();
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
      </section>

      <section className="planner-section" id="planner" aria-labelledby="planner-title">
        <div className="section-navigation"><div className="steps"><span className={view === 'field' ? 'active' : 'complete'}><b>{view === 'results' ? <Check size={14}/> : '01'}</b>{m.stepOne}</span><i/><span className={view === 'results' ? 'active' : ''}><b>02</b>{m.stepTwo}</span></div></div>

        {view === 'field' || !comparison ? <>
          {pending ? <CalculationLoading inputs={inputs} language={language} headingRef={calculationHeading}/> : <h2 id="planner-title" className="sr-only" tabIndex={-1} ref={formHeading}>{m.stepOne}</h2>}
          {loadingCatalog && <p className="model-status" role="status">{m.loadingCatalog}</p>}
          {serviceError && <div className="form-error" role="alert" tabIndex={-1} ref={errorRef}><Info size={19}/><div><strong>{m.errors[serviceError.kind]}</strong>{serviceError.requestId && <small>{serviceError.requestId}</small>}{serviceError.kind === 'validation' && <ul>{Object.entries(serviceError.fields).map(([field, messages]) => <li key={field}>{field}: {messages.join(' ')}</li>)}</ul>}{!catalog && <button type="button" className="button secondary" onClick={() => setCatalogAttempt(value => value + 1)}>{m.retry}</button>}</div></div>}
          <div hidden={pending}><div className="form-layout"><form onSubmit={submit} noValidate aria-busy={!ready || pending || loadingCatalog}><fieldset className="interactive-fields" disabled={!ready || pending || loadingCatalog}>
            {error && <div className="form-error" role="alert" tabIndex={-1} ref={errorRef}><Info size={19}/><div><strong>{m.validationTitle}</strong><p>{m.errors[error]}</p></div></div>}
            <div className="form-card"><div className="card-heading"><span className="section-icon"><Earth size={21}/></span><div><h3>{m.fieldHeading}</h3><p>{m.fieldSub}</p></div><span className="card-number">01</span></div>
              <div className="two-columns"><div className="field"><label htmlFor="location">{m.f_place}</label><div className="select-wrap"><MapPin size={16}/><select id="location" value={inputs.place} onChange={event => update('place', event.target.value)} aria-describedby="pilot-hint">{catalog?.places.map(place => <option key={place.id} value={place.id}>{place.name}, {place.province}</option>)}</select><ChevronDown size={15}/></div><p className="field-hint" id="pilot-hint">{m.pilotOnly}</p></div><div className="field"><label htmlFor="main-crop">{m.mainCrop}</label><div className="select-wrap"><select id="main-crop" value={inputs.main_crop} onChange={event => update('main_crop', event.target.value)}>{catalog?.capabilities?.includes('fallow') && <option value="fallow">{m.fallow}</option>}{catalog?.crops.map(crop => <option key={crop.id} value={crop.id}>{language === 'en' ? crop.name : crop.local_name}</option>)}</select><ChevronDown size={15}/></div></div></div>
              <fieldset aria-describedby="drainage-hint"><legend>{m.f_pond}</legend><Choice value={inputs.drainage} label={m.f_pond} onChange={value => update('drainage', value)} options={[{ value: 'well_drained', label: m.no }, { value: 'poorly_drained', label: m.yes }, { value: 'unknown', label: m.unsure }]}/><p className="field-hint" id="drainage-hint">{m.drainageHint}</p></fieldset>
              <fieldset><legend>{m.f_water}</legend><Choice value={inputs.water} label={m.f_water} onChange={value => update('water', value)} options={[{ value: 'rain', label: m.w_rain, icon: <CloudRain size={19}/> }, { value: 'irrigation', label: m.w_irrig, icon: <Waves size={19}/> }]}/></fieldset>
              {inputs.water === 'irrigation' && inputs.drainage === 'poorly_drained' && <p className="field-hint">{m.irrigationDrainageNote}</p>}
            </div>
            <div className="form-card"><div className="card-heading"><span className="section-icon"><CalendarDays size={21}/></span><div><h3>{m.calendarHeading}</h3><p>{m.calendarSub}</p></div><span className="card-number">02</span></div>
              <div className="two-columns"><div className="field"><label htmlFor="harvest">{inputs.main_crop === 'fallow' ? m.fieldAvailable : m.f_harvest}</label><input required type="date" id="harvest" value={inputs.harvest} aria-invalid={error === 'dates' || error === 'order'} onChange={event => update('harvest', event.target.value)}/></div><div className="field"><label htmlFor="next">{m.f_next}</label><input required type="date" id="next" value={inputs.next_planting} aria-invalid={error === 'dates' || error === 'order'} onChange={event => update('next_planting', event.target.value)}/></div></div>
            </div>
            <div className="form-card"><label className="soil-toggle"><input type="checkbox" checked={soilTest} onChange={event => { setSoilTest(event.target.checked); if (!event.target.checked) { update('soil_ph', ''); update('soil_texture', ''); } }}/>{m.soilTest}</label><p className="field-hint">{m.soilHint}</p>{soilTest && <div className="two-columns"><div className="field"><label htmlFor="ph">{m.f_ph}</label><input id="ph" type="number" min="3" max="10" step="any" inputMode="decimal" value={inputs.soil_ph} onChange={event => update('soil_ph', event.target.value)} aria-invalid={error === 'ph'}/></div><div className="field"><label htmlFor="soil-texture">{m.soilTexture}</label><select id="soil-texture" value={inputs.soil_texture} onChange={event => update('soil_texture', event.target.value as FieldInputs['soil_texture'])}><option value="">{m.dontknow}</option>{(['light', 'medium', 'heavy'] as const).map(value => <option key={value} value={value}>{m.texture[value]}</option>)}</select></div></div>}</div>
            <div className="form-card priority-card"><fieldset><legend>{m.priority}</legend><Choice value={priority} onChange={setPriority} label={m.priority} options={[{ value: 'balanced', label: m.p_even }, { value: 'saving_water', label: m.p_water }, { value: 'healthier_soil', label: m.p_soil }, { value: 'finishing_early', label: m.p_time }]}/></fieldset></div>
            <details className="form-card model-settings"><summary>{m.advanced}<ChevronDown size={16}/></summary><div className="schedule-settings"><h3>{m.scheduleTitle}</h3><p className="field-hint">{m.scheduleHint}</p><div className="schedule-fields">
              <div className="field"><label htmlFor="prep-days">{m.prepDays}</label><input id="prep-days" type="number" min="0" max="180" step="1" inputMode="numeric" value={inputs.prep_days} onChange={event => update('prep_days', event.target.value)} aria-describedby="prep-days-hint" aria-invalid={error === 'prepDays'}/><p className="field-hint" id="prep-days-hint">{m.prepDaysHint}</p></div>
              <div className="field"><label htmlFor="picking-days">{m.pickingDays}</label><input id="picking-days" type="number" min="0" max="180" step="1" inputMode="numeric" value={inputs.picking_days} onChange={event => update('picking_days', event.target.value)} aria-describedby="picking-days-hint" aria-invalid={error === 'pickingDays'}/><p className="field-hint" id="picking-days-hint">{m.pickingDaysHint}</p></div>
              <div className="field"><label htmlFor="preparation">{m.clearingDays}</label><input id="preparation" type="number" min="0" max="90" step="1" inputMode="numeric" value={inputs.turnaround_days} onChange={event => update('turnaround_days', event.target.value)} aria-describedby="clearing-hint" aria-invalid={error === 'preparation'}/><p className="field-hint" id="clearing-hint">{m.clearingDaysHint}</p></div>
            </div></div><div className="field"><label htmlFor="pass-mark">{m.passMark}</label><input id="pass-mark" type="number" min="0" max="1" step="any" value={inputs.pass_mark} onChange={event => update('pass_mark', event.target.value)} aria-describedby="pass-hint"/><p className="field-hint" id="pass-hint">{m.passHint}</p></div></details>
            <div className="form-actions"><p><ShieldCheck size={17}/>{m.savedLocally}</p><button className="button primary" type="submit" disabled={!catalog || pending || loadingCatalog}>{serviceError ? m.retry : m.go}<ArrowRight size={19}/></button></div>
          </fieldset></form>
          <aside className="planner-aside"><div className="window-card"><div className="window-top"><CalendarDays size={20}/><span className="micro-label">{m.windowLabel}</span></div><div className="window-value"><strong>{days > 0 ? days : '—'}</strong><span>{m.available}</span></div><div className="season-lines" aria-hidden="true"><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/></div><div className="window-dates"><div><span className="timeline-dot"/><div><small>{inputs.main_crop === 'fallow' ? m.fieldAvailable : m.riceHarvest}</small><strong>{dateLabel(inputs.harvest, language)}</strong></div></div><i/><div><span className="timeline-dot end"/><div><small>{m.nextPlanting}</small><strong>{dateLabel(inputs.next_planting, language)}</strong></div></div></div><p>{days > 0 ? m.calendarNote : m.nothingYet}</p></div><div className="aside-note"><CircleHelp size={21}/><p>{m.formNote}</p></div></aside></div></div>
        </> : <>
          <div className="section-heading results-heading"><div><span className="eyebrow">{m.resultsKicker}</span><h2 id="planner-title" tabIndex={-1} ref={resultsHeading}>{m.r_title}</h2><p>{m.resultsIntro}</p></div><button className="button secondary" onClick={showForm}><ArrowLeft size={16}/>{m.edit}</button></div>
          {catalog && <ResultOverview comparison={comparison} catalog={catalog} language={language} m={m}/>}
          {catalog && <RecommendationNotice comparison={comparison} catalog={catalog} language={language} m={m}/>}
          <div className="results-notice"><Info size={18}/><p><strong>{m.resultsLabel}.</strong> {m.modelLimits}</p></div>
          <div className="results-layout"><aside className="filter-card" aria-label={m.filtersTitle}><div className="filter-scroll" tabIndex={0} aria-label={m.filtersTitle}><div className="filter-heading"><SlidersHorizontal size={20}/><h3>{m.filtersTitle}</h3></div><div className="detail-switch" role="group" aria-label={m.resultView}><button type="button" aria-pressed={!detailed} onClick={() => setDetailed(false)}>{m.simpleView}</button><button type="button" aria-pressed={detailed} onClick={() => setDetailed(true)}>{m.moreDetailed}</button></div><p className="filter-explainer">{m.filtersHint}</p><fieldset><legend>{m.season}</legend><Choice className="vertical" value={season} onChange={setSeason} label={m.season} options={[
            { value: 'all', label: m.allSeasons, icon: <Earth size={18}/> }, { value: 'normal', label: m.s_typical, icon: <Sun size={18}/> }, { value: 'dry', label: m.s_dry, icon: <Thermometer size={18}/> }, { value: 'el_nino', label: m.s_nino, icon: <CloudRain size={18}/> },
          ]}/></fieldset><fieldset><legend>{m.priority}</legend><Choice className="vertical" value={priority} onChange={setPriority} label={m.priority} options={[
            { value: 'balanced', label: m.p_even, icon: <SlidersHorizontal size={18}/> }, { value: 'saving_water', label: m.p_water, icon: <Droplets size={18}/> }, { value: 'healthier_soil', label: m.p_soil, icon: <Leaf size={18}/> }, { value: 'finishing_early', label: m.p_time, icon: <CalendarDays size={18}/> },
          ]}/></fieldset></div><div className="filter-reset"><button className="text-button" onClick={reset}><RotateCcw size={16}/>{m.reset}</button></div></aside><div className="crop-area"><div className="crop-area-heading"><h3>{format(m.compareCount, { n: options.length })}</h3><div className="active-filters" aria-label={m.selectedFilters} aria-live="polite"><span>{seasonLabel}</span><span>{priorityLabel}</span><span>{comparison.inputs.water === 'irrigation' ? m.w_irrig : m.w_rain}</span></div></div><div className="crop-grid">{options.map(option => <CropCard key={option.crop.id} option={option} days={comparison.results.meta.window_days} language={language} m={m} mainCrop={applied.main_crop} season={season} detailed={detailed} comparison={comparison}/>)}</div></div></div>
          <div className="results-actions"><button className="button secondary" onClick={download}><Download size={17}/>{m.download}</button></div>
        </>}
      </section>


    </main>
    <SiteFooter language={language}/>
    {toast && <div className="toast" role="status"><Check size={18}/>{m.downloaded}</div>}
  </div></AppIntro>;
}
