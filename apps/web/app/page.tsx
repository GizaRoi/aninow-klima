'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ArrowUpRight, ArrowLeft, Bookmark, CalendarDays, Check, CheckCircle2, ChevronDown, CircleHelp, CloudRain, Download, Droplets, ExternalLink, History, Info, LayoutDashboard, Leaf, MapPin, Menu, Plus, RotateCcw, Satellite, ShieldCheck, SlidersHorizontal, Sprout, Sun, Thermometer, Users, Wallet, Wheat, X } from 'lucide-react';
import { defaults, priorities, evaluate, validateInputs, php, dateLabel, type Inputs, type Result, type SavedPlan, type Priority } from '../lib/demo';

import powerSample from '../lib/power-sample.json';
import { LanguageProvider, LanguageSwitch, useLanguage } from '../lib/language';
import { localizeResult } from '../lib/translations';

type View = 'overview' | 'planner' | 'results' | 'history' | 'sources' | 'team';
const nav = [
  { id: 'overview', label: 'My field', icon: LayoutDashboard },
  { id: 'planner', label: 'Plan next planting', icon: Sprout },
  { id: 'history', label: 'Saved comparisons', icon: History },
  { id: 'sources', label: 'Data & challenge', icon: Satellite },
  { id: 'team', label: 'Our team', icon: Users },
] as const;
const team = [
  { name: 'Romano Franco Huraño', photo: 'romano-franco-hurano.webp' },
  { name: 'Christian Paul Godilano', photo: 'christian-paul-godilano.webp' },
  { name: 'Roimarc Bilbao', photo: 'roimarc-bilbao.png' },
  { name: 'Yuan Yancey Labay', photo: 'yuan-yancey-labay.webp' },
];
const sourceLinks = [
  { name: 'Field Shift challenge', type: 'Verified challenge brief', url: 'https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/', description: 'Use NASA Earth observations, local soil information, crop characteristics and farmer priorities to explore rotation strategies.' },
  { name: '2026 participation & submission', type: 'Verified event overview', url: 'https://www.spaceappschallenge.org/2026/', description: 'Register, select an event, form a team of at most six, and submit through the project tab. The event page lists November 14–15, 2026; confirm the applicable local deadline.' },
  { name: 'Participant resources', type: 'Current guides need confirmation', url: 'https://www.spaceappschallenge.org/resources/', description: 'The current submission and judging guide pages were not reliably retrievable during this build. Verify their exact requirements with your Local Lead; older-year guides are not treated as 2026 rules.' },
  { name: 'NASA POWER', type: 'Archived real sample · available', url: 'https://power.larc.nasa.gov/docs/services/api/temporal/daily/', description: 'The dashboard uses real daily values for 1–30 January 2024 (UTC) at 15.48°N, 120.59°E. Values represent regional source grids. They do not drive the synthetic crop checks.' },
  { name: 'GPM / IMERG', type: 'Planned integration · not connected', url: 'https://gpm.nasa.gov/data/imerg', description: 'Satellite precipitation evidence. Product, run, units, native grid and availability must be pinned before ingestion.' },
  { name: 'Local crop evidence', type: 'Reference · not a published profile', url: 'https://library.buplant.da.gov.ph/images/1640929884The%20Mungbean%20Plant.pdf', description: 'A BPI reference supports investigating mungbean rotations. The numeric fixtures in this prototype are not taken from this guide and are not validated recommendations.' },
];

function DateInput({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [text, setText] = useState(() => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    return match ? `${match[2]}/${match[3]}/${match[1]}` : '';
  });
  return <input type="text" inputMode="numeric" placeholder="MM/DD/YYYY" value={text} onChange={event => {
    const digits = event.target.value.replace(/\D/g, '').slice(0, 8);
    const formatted = [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4)].filter(Boolean).join('/');
    setText(formatted);
    onChange(digits.length === 8 ? `${digits.slice(4)}-${digits.slice(0, 2)}-${digits.slice(2, 4)}` : '');
  }}/>;
}

function FieldMap({ dark = false }: { dark?: boolean }) {
  const { t } = useLanguage();
  const [layer, setLayer] = useState('Field');
  return <div className={`field-map ${dark ? 'dark-map' : ''}`}>
    <svg viewBox="0 0 800 450" role="img" aria-label={t("Illustrated example farmland with a highlighted field. This is not satellite imagery.")}>
      <defs>
        <pattern id={dark ? 'rows-dark' : 'rows-light'} width="11" height="11" patternUnits="userSpaceOnUse" patternTransform="rotate(-27)"><path d="M 0 0 L 0 11" stroke={dark ? '#bdd7a3' : '#789a6a'} strokeWidth="3" opacity=".3" /></pattern>
        <filter id="field-shadow"><feDropShadow dx="0" dy="8" stdDeviation="10" floodColor="#173e29" floodOpacity=".2" /></filter>
      </defs>
      <rect width="800" height="450" fill={dark ? '#294b36' : '#dfe7d3'} />
      <g stroke={dark ? '#456347' : '#d2dcc5'} strokeWidth="9" strokeLinejoin="round">
        <path d="M-30 -20 205 -20 239 110 83 197 -30 145Z" fill="#97ad77" />
        <path d="M218 -20 464 -20 477 100 250 118Z" fill="#b6c48a" />
        <path d="M478 -20 710 -20 674 109 490 100Z" fill="#739260" />
        <path d="M724 -20 830 -20 830 190 688 113Z" fill="#a9b880" />
        <path d="M-20 160 77 211 112 354 -20 405Z" fill="#9eaf79" />
        <path d="M90 211 251 124 314 270 124 352Z" fill="#b9c895" />
        <path d="M263 128 480 113 494 265 326 272Z" fill={layer === 'Water' ? '#8bbaa9' : '#668a50'} />
        <path d="M496 115 675 123 665 282 508 266Z" fill="#a7b77e" />
        <path d="M688 128 830 203 830 340 679 283Z" fill="#7f9b66" />
        <path d="M-20 421 123 370 214 480 -20 480Z" fill="#78975f" />
        <path d="M137 365 319 287 388 480 228 480Z" fill="#b4bf86" />
        <path d="M332 287 499 281 565 480 401 480Z" fill="#8da46d" />
        <path d="M514 282 665 296 739 480 580 480Z" fill="#c3ca93" />
        <path d="M680 299 830 356 830 480 751 480Z" fill="#91a473" />
      </g>
      <g fill={`url(#${dark ? 'rows-dark' : 'rows-light'})`}><path d="M90 211 251 124 314 270 124 352Z"/><path d="M496 115 675 123 665 282 508 266Z"/><path d="M137 365 319 287 388 480 228 480Z"/><path d="M514 282 665 296 739 480 580 480Z"/></g>
      <path d="M-40 42 C100 27 77 123 159 153 S300 169 265 240 317 346 437 345 511 441 574 480" fill="none" stroke={dark ? '#658775' : '#b7cbd0'} strokeWidth="19" />
      <path d="M-40 42 C100 27 77 123 159 153 S300 169 265 240 317 346 437 345 511 441 574 480" fill="none" stroke={dark ? '#88a693' : '#d0e0e0'} strokeWidth="9" />
      <path d="M263 128 480 113 494 265 326 272Z" fill="#b9d97c" fillOpacity=".45" stroke="#e8ffb5" strokeWidth="4" strokeDasharray="9 6" filter="url(#field-shadow)" />
      <g transform="translate(397 191)"><circle r="34" fill="white" fillOpacity=".2"/><circle r="23" fill="#f7ffdd"/><path d="M0 9 V-7 M0 0 C-11 0 -12 -10 -12 -10 C0 -11 0 0 0 0 M0 -3 C11 -3 12 -13 12 -13 C0 -14 0 -3 0 -3" fill="none" stroke="#32583a" strokeWidth="2.5" strokeLinecap="round"/></g>
      <g transform="translate(354 235)"><rect width="95" height="30" rx="15" fill="#173f2c"/><text x="47.5" y="20" textAnchor="middle" fill="white" fontSize="12" fontFamily="sans-serif">{t("Field 01 · 1 ha")}</text></g>
    </svg>
    <div className="map-switch" aria-label={t("Illustration display layer")}>{['Field', 'Water'].map(l => <button key={l} className={layer === l ? 'active' : ''} onClick={() => setLayer(l)}>{t(l)}</button>)}</div>
    <span className="map-north">N <span>{t("↑")}</span></span>
    <span className="map-credit">{t("Illustrative map · no satellite data")}</span>
  </div>;
}

function Status({ result }: { result: Pick<Result, 'feasibility'> }) {
  const { t } = useLanguage();
  const label = result.feasibility === 'feasible' ? 'Fits this demo' : result.feasibility === 'unknown' ? 'Needs confirmation' : 'Constraint found';
  return <span className={`status ${result.feasibility}`}><span/>{t(label)}</span>;
}

function ClimateChart() {
  const { t } = useLanguage();
  const values = Object.values(powerSample.raw.properties.parameter.T2M_MAX);
  const low = Math.floor(Math.min(...values));
  const high = Math.ceil(Math.max(...values));
  const points = values.map((value, index) => `${8 + index * 264 / (values.length - 1)},${78 - (value - low) * 60 / (high - low)}`).join(' ');
  return <div className="climate-chart">
    <svg viewBox="0 0 280 104" role="img" aria-label={t('Archived daily maximum temperatures, 1 to 30 January 2024, ranging from {low} to {high} degrees Celsius.', { low: Math.min(...values).toFixed(1), high: Math.max(...values).toFixed(1) })}>
      <defs><linearGradient id="climate-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#d5ef7d" stopOpacity=".4"/><stop offset="100%" stopColor="#d5ef7d" stopOpacity="0"/></linearGradient></defs>
      <path d="M8 26H272 M8 54H272 M8 82H272" className="chart-grid"/>
      <polygon points={`8,88 ${points} 272,88`} fill="url(#climate-fill)"/>
      <polyline points={points} fill="none" stroke="#f4f5e8" strokeWidth="1.8" strokeLinejoin="round"/>
      {values.map((value, index) => index % 5 === 0 && <circle key={index} cx={8 + index * 264 / (values.length - 1)} cy={78 - (value - low) * 60 / (high - low)} r="2.5" fill="#d5ef7d"/>)}
      <text x="8" y="102">{t("01 Jan")}</text><text x="123" y="102">{t("15 Jan")}</text><text x="242" y="102">{t("30 Jan")}</text>
    </svg>
  </div>;
}

export default function Home() {
  return <LanguageProvider><Prototype/></LanguageProvider>;
}

function Prototype() {
  const { t, language } = useLanguage();
  const [view, setView] = useState<View>('overview');
  const [inputs, setInputs] = useState<Inputs>({ ...defaults });
  const [applied, setApplied] = useState<Inputs>({ ...defaults });
  const [saved, setSaved] = useState<SavedPlan[]>([]);
  const [detail, setDetail] = useState<string | null>(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [headerScrolled, setHeaderScrolled] = useState(false);
  const [toast, setToast] = useState('');
  const [error, setError] = useState('');
  const dialogRef = useRef<HTMLElement>(null);
  const results = evaluate(applied).map(result => localizeResult(result, applied, language));
  const selected = results.find(r => r.id === detail);
  useEffect(() => {
    const updateHeader = () => setHeaderScrolled(window.scrollY > 4);
    updateHeader();
    window.addEventListener('scroll', updateHeader, { passive: true });
    return () => window.removeEventListener('scroll', updateHeader);
  }, []);
  useEffect(() => {
    try {
      const raw: unknown = JSON.parse(sessionStorage.getItem('aninow-demo-plans-v1') ?? '[]');
      if (Array.isArray(raw)) setSaved(raw.filter((p): p is SavedPlan => typeof p?.id === 'string' && typeof p?.savedAt === 'string' && p?.inputs && !validateInputs(p.inputs)).slice(0, 20));
    } catch { /* Invalid or unavailable session storage leaves an empty demo history. */ }
  }, []);
  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(''), 4000); return () => clearTimeout(t); } }, [toast]);
  useEffect(() => {
    if (!detail) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDetail(null);
      if (event.key === 'Tab') {
        const elements = dialogRef.current?.querySelectorAll<HTMLElement>('button, a[href], input, select, [tabindex="0"]');
        if (!elements?.length) return;
        const first = elements[0], last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', onEscape);
    return () => { document.removeEventListener('keydown', onEscape); document.body.style.overflow = previousOverflow; previousFocus?.focus(); };
  }, [detail]);
  const go = (next: View) => { setView(next); setMobileNav(false); setError(''); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  const set = <K extends keyof Inputs>(key: K, value: Inputs[K]) => setInputs(p => ({ ...p, [key]: value }));
  const compare = (event: React.FormEvent) => {
    event.preventDefault();
    const problem = validateInputs(inputs);
    if (problem) { setError(problem); return; }
    setApplied({ ...inputs }); go('results');
  };
  const save = () => {
    const plan: SavedPlan = { id: crypto.randomUUID(), savedAt: new Date().toISOString(), inputs: { ...applied } };
    const next = [plan, ...saved].slice(0, 20);
    try { sessionStorage.setItem('aninow-demo-plans-v1', JSON.stringify(next)); setSaved(next); setToast('Comparison saved for this browser session.'); }
    catch { setToast('Browser storage is unavailable. You can still explore this comparison.'); }
  };
  const download = () => {
    const blob = new Blob([JSON.stringify({ notice: 'Synthetic demo fixtures. Not farm advice or NASA observations.', inputs: applied, results }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'aninow-demo-comparison.json'; a.click(); URL.revokeObjectURL(url);
  };
  const clearSaved = () => { try { sessionStorage.removeItem('aninow-demo-plans-v1'); setSaved([]); setToast('Demo session history cleared.'); } catch { setToast('Browser storage is unavailable.'); } };

  return <div className={`app-shell view-${view}`}>
    <a className="skip-link" href="#main">{t("Skip to main content")}</a>
    <header className={`site-header${headerScrolled ? ' is-scrolled' : ''}`}>
    <button className="header-menu icon-button" aria-label={t("Open navigation")} onClick={() => setMobileNav(true)}><Menu size={22}/></button>
    <div className="mobile-header-brand"><span className="brand-icon"><Sprout size={19}/></span><strong>AniNow</strong></div>
    {mobileNav && <button className="nav-scrim" aria-label={t("Close navigation")} onClick={() => setMobileNav(false)}/>}
    <aside className={`sidebar ${mobileNav ? 'open' : ''}`}>
      <button className="brand" onClick={() => go('overview')} aria-label={t("AniNow Klima home")}><span className="brand-icon"><Sprout size={25}/></span><span>AniNow<span className="brand-sub">KLIMA</span></span></button>
      <div className="workspace-label">{t("YOUR GROWING SPACE")}</div>
      <nav aria-label={t("Main navigation")}>{nav.map(item => <button key={item.id} onClick={() => go(item.id)} className={view === item.id || (view === 'results' && item.id === 'planner') ? 'nav-item selected' : 'nav-item'} aria-current={view === item.id ? 'page' : undefined}><item.icon size={19}/>{t(item.label)}{item.id === 'history' && saved.length > 0 && <span className="nav-count">{saved.length}</span>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="orbit-icon"><Satellite size={22}/></div><p>{t("From space.")}<br/><strong>{t("To your field.")}</strong></p><span>NASA Space Apps 2026<br/>{t("Field Shift project")}</span><div className="sidebar-divider"/><button className="help-link" onClick={() => go('sources')}><CircleHelp size={17}/>  {t("About this prototype")} <ArrowUpRight size={14}/></button></div>
      <div className="profile"><span className="avatar">DF</span><span><strong>{t("Demo farmer")}</strong><small>{t("Explore your sample field")}</small></span><span className="profile-dot"/></div>
    </aside>
    <LanguageSwitch/>
    </header>

    <div className="main-shell">
      <main id="main" tabIndex={-1}>
        {view === 'overview' && <>
          <section className="landscape-hero" aria-label={t("Your next planting")}>
            <img className="landscape-image" src="/images/farm-diorama.png" alt={t("An artistic three-dimensional rice farm with green and golden crop plots floating in soft mist.")} fetchPriority="high"/>
            <div className="landscape-shade"/>
            <div className="landscape-copy"><span className="scene-kicker"><Sprout size={13}/>  {t("A new season of possibilities")}</span><h1>{t("Let’s grow")}<br/>{t("what comes next.")}</h1><p>{t("Your field. A little evidence.")}<br/>{t("A clearer path to your next planting.")}</p><button className="button scene-cta" onClick={() => go('planner')}>{t("Plan next planting")} <ArrowUpRight size={17}/></button></div>
            <span className="scene-location"><MapPin size={13}/>  {t("Tarlac, Philippines")} <span>{t("15.48° N · 120.59° E")}</span></span>
            <section className="glass-panel field-glass"><div className="glass-title"><h2>{t("Your field, in focus.")}</h2><button className="glass-icon" aria-label={t("Edit sample field details")} onClick={() => go('planner')}><ArrowUpRight size={18}/></button></div><p className="glass-caption">{t("Maligaya field")} <span>{t("Sample field · 01")}</span></p><div className="glass-field-metrics"><div><span>{t("Field area")}</span><strong>{applied.area.toFixed(1)}<small> ha</small></strong></div><div><span>{t("Previous crop")}</span><strong>{t("Rice")}<small>{language === "tl" ? " / Rice" : " / Palay"}</small></strong></div></div><div className="glass-field-footer"><span className="lime-dot"/>{t(applied.water === 'limited' ? 'Limited irrigation' : applied.water === 'reliable' ? 'Reliable irrigation' : 'No irrigation')}<span>{t("Demo scenario")}</span></div></section>
            <section className="glass-panel climate-glass"><div className="glass-title"><h2>{t("A little climate context.")}</h2><Satellite size={17}/></div><p className="glass-caption">{t("Daily maximum temperature")} <span>{t("Archived")}</span></p><div className="glass-temperature"><strong>{powerSample.meanDailyMaximumC.toFixed(1)}<small>{t("°C")}</small></strong><span>{t("Mean daily maximum")}<br/>{t("1–30 Jan 2024 · UTC")}</span></div><ClimateChart/><a className="glass-source" href={powerSample.sourceUrl} target="_blank" rel="noreferrer">NASA POWER <ArrowUpRight size={12}/><span>{t("Regional context")}</span></a></section>
            <div className="scene-bottom"><span><span className="lime-dot"/>  {t("Interactive prototype")} <span className="scene-art-note">{t("· Concept artwork, not satellite imagery")}</span></span><a href="#field-snapshot">{t("Scroll to explore")} <ChevronDown size={15}/></a></div>
          </section>
          <div className="overview-intro"><span className="scene-kicker"><Leaf size={13}/>  {t("Rooted in your reality")}</span><h2>{t("Every next season")}<br/>{t("starts with")} <em>{t("your field.")}</em></h2><p>{t("A familiar crop or a fresh rotation? Explore what fits your water, budget, and planting window before you decide.")}</p></div>
          <div id="field-snapshot" className="snapshot-anchor"/>
          <div className="section-heading"><div><span className="section-index">01</span><h2>{t("A snapshot of your field")}</h2></div><span className="muted-small">{t("Example location · Tarlac, Central Luzon")}</span></div>
          <div className="field-grid"><section className="field-card"><div className="field-card-heading"><span className="field-icon"><Wheat size={22}/></span><span><p className="overline">{t("YOUR SAMPLE FIELD")}</p><h3>{t("Maligaya field")} <span>01</span></h3></span><button className="icon-button edit-field" aria-label={t("Edit sample field details")} onClick={() => go('planner')}><SlidersHorizontal size={17}/></button></div><div className="field-facts"><div><span>{t("Field area")}</span><strong>{applied.area.toFixed(1)} <small>{t(applied.area !== 1 ? 'hectares' : 'hectare')}</small></strong></div><div><span>{t("Previous crop")}</span><strong>{t("Rice")} <small>{language === 'tl' ? 'Rice' : 'Palay'}</small></strong></div><div><span>{t("Water access")}</span><strong>{t(applied.water === 'limited' ? 'Limited' : applied.water === 'reliable' ? 'Reliable' : 'None')} <small>{t("irrigation")}</small></strong></div></div><div className="field-card-bottom"><MapPin size={14}/><span>{t("Illustrative field · no approved pilot yet")}</span></div></section>
          <div className="condition-card"><div className="condition-icon warm"><Thermometer size={21}/></div><span className="overline">{t("MEAN DAILY MAXIMUM")}</span><strong>{powerSample.meanDailyMaximumC.toFixed(1)}<span>{t("°C")}</span></strong><p>{t("1–30 Jan 2024 · UTC")}</p><a className="sample-tag" href={powerSample.sourceUrl} target="_blank" rel="noreferrer">{t("NASA POWER · archived ↗")}</a></div><div className="condition-card"><div className="condition-icon blue"><CloudRain size={21}/></div><span className="overline">{t("TOTAL PRECIPITATION")}</span><strong>{powerSample.precipitationTotalMm}<span> mm</span></strong><p>{t("1–30 Jan 2024 · UTC")}</p><a className="sample-tag" href={powerSample.sourceUrl} target="_blank" rel="noreferrer">{t("NASA POWER · archived ↗")}</a></div></div>
          <div className="overview-bottom"><section className="next-card"><div className="section-heading"><div><span className="section-index">02</span><h2>{t("What could come after rice?")}</h2></div><button className="text-button" onClick={() => go('planner')}>{t("Explore options")} <ArrowRight size={15}/></button></div><div className="mini-crops">{results.map(crop => <button className="mini-crop" key={crop.id} onClick={() => { setApplied({ ...applied }); setDetail(crop.id); }}><span className={`crop-glyph ${crop.id}`}>{crop.id === 'rice' ? <Wheat size={30}/> : <Sprout size={30}/>}</span><span className="mini-crop-copy"><small>{t(crop.kind)}</small><strong>{t(crop.name)} <em>{crop.localName}</em></strong><span>{t(crop.id === 'rice' ? 'Check water and starting costs' : 'Check drainage and buyer access')}</span></span><ArrowUpRight size={19}/></button>)}</div><div className="gentle-note"><Info size={15}/><span>{t("Explore tradeoffs first. There is no automatic “best crop.”")}</span></div></section><section className="evidence-card"><span className="evidence-orbit"><Satellite size={24}/></span><p className="overline">{t("A BIGGER PICTURE")}</p><h3>{t("Space data.")}<br/>{t("Local understanding.")}</h3><p>{t("Archived climate context is here. Locally reviewed crop comparisons come next.")}</p><button className="text-button" onClick={() => go('sources')}>{t("See the data plan")} <ArrowUpRight size={15}/></button><div className="source-chips"><span>NASA POWER</span><span>GPM / IMERG</span></div></section></div>
        </>}

        {view === 'planner' && <>
          <div className="page-heading"><div><p className="eyebrow">{t("YOUR NEXT PLANTING · SUSUNOD NA TANIM")}</p><h1>{t("Start with your circumstances.")}</h1><p>{t("A few details help make the comparison more useful.")}</p></div><button className="button secondary" onClick={() => { setInputs({ ...defaults }); setError(''); }}><RotateCcw size={16}/>  {t("Reset example")}</button></div>
          <form onSubmit={compare} noValidate className="planner-layout"><div className="form-stack">
            <section className="form-card"><div className="form-title"><span>01</span><div><h2>{t("Your field & planting window")}</h2><p>{t("One field. One next planting. Rice stays in the comparison.")}</p></div></div><div className="form-grid"><label>{t("Field area")} <span className="input-unit"><input type="number" min="0.1" max="10" step="0.1" value={Number.isNaN(inputs.area) ? '' : inputs.area} onChange={e => set('area', e.target.value === '' ? NaN : Number(e.target.value))}/> <span>{t("hectares")}</span></span></label><label>{t("Proposed planting date")}<DateInput value={inputs.plantingDate} onChange={value => set('plantingDate', value)}/><small>MM/DD/YYYY</small></label><label className="full-width">{t("Field must be ready for rice again by")}<DateInput value={inputs.riceDeadline} onChange={value => set('riceDeadline', value)}/><small>MM/DD/YYYY · {t("Includes the demo crop’s growing period and time to prepare the field.")}</small></label></div></section>
            <section className="form-card"><div className="form-title"><span>02</span><div><h2>{t("What are you working with?")}</h2><p>{t("“I’m not sure” is a useful answer, too.")}</p></div></div><div className="form-grid"><label>{t("Irrigation availability")}<select value={inputs.water} onChange={e => set('water', e.target.value as Inputs['water'])}><option value="limited">{t("Limited · 200 mm demo supply")}</option><option value="reliable">{t("Reliable · 800 mm demo supply")}</option><option value="none">{t("No irrigation · 0 mm demo supply")}</option></select></label><label>{t("Field drainage")}<select value={inputs.drainage} onChange={e => set('drainage', e.target.value as Inputs['drainage'])}><option value="unknown">{t("I’m not sure yet")}</option><option value="well_drained">{t("Drains well after rain")}</option><option value="waterlogging">{t("Water stays pooled")}</option></select></label><label>{t("Starting cash budget")}<span className="input-unit"><span>{t("₱")}</span><input type="number" min="0" step="1000" value={Number.isNaN(inputs.budget) ? '' : inputs.budget} onChange={e => set('budget', e.target.value === '' ? NaN : Number(e.target.value))}/></span><small>{t("Total allocated through planting, including already-paid next-crop costs.")}</small></label><label>{t("Buyer access for both demo crops")}<select value={inputs.buyer} onChange={e => set('buyer', e.target.value as Inputs['buyer'])}><option value="unknown">{t("Not confirmed yet")}</option><option value="available">{t("A buyer is available")}</option><option value="unavailable">{t("No buyer available")}</option></select><small>{t("The full app will record buyer access separately for each crop.")}</small></label></div></section>
            <section className="form-card"><div className="form-title"><span>03</span><div><h2>{t("What matters most this season?")}</h2><p>{t("A priority helps explain tradeoffs. It never overrides a constraint.")}</p></div></div><div className="priority-options" role="radiogroup" aria-label={t("Planting priority")}>{priorities.map((p, index) => { const Icon = [Droplets, Wallet, CalendarDays, Leaf, Sun][index]; return <label className={`priority-option ${inputs.priority === p.id ? 'chosen' : ''}`} key={p.id}><input type="radio" name="priority" value={p.id} checked={inputs.priority === p.id} onChange={() => set('priority', p.id)}/><Icon size={20}/><span><strong>{t(p.label)}</strong><small>{t(p.description)}</small></span><span className="radio-dot"/></label>; })}</div></section>
            <section className="simulation-option"><label><input type="checkbox" checked={inputs.simulation} onChange={e => set('simulation', e.target.checked)}/><span><strong>{t("Include an illustrative harvest & income scenario")}</strong><small>{t("Uses fictional yield, price and cost assumptions. No trained model is connected.")}</small></span></label></section>
            {error && <div className="form-error" role="alert"><Info size={18}/>{t(error)}</div>}
            <div className="form-actions"><button type="button" className="text-button" onClick={() => go('overview')}><ArrowLeft size={16}/>  {t("Back to field")}</button><button type="submit" className="button primary">{t("Compare planting options")} <ArrowRight size={17}/></button></div>
          </div><aside className="planner-aside"><div className="sticky-aside"><div className="aside-map"><FieldMap/></div><div className="aside-summary"><span className="overline">{t("MALIGAYA FIELD · DEMO")}</span><h3>{t("Your field comes first.")}</h3><p>{t("The same planting window, area and constraints apply to both crops.")}</p><div className="aside-divider"/><span className="aside-line"><Wheat size={17}/>  {t("Rice is your baseline")}</span><span className="aside-line"><Sprout size={17}/>  {t("Mungbean is an example alternative")}</span><span className="aside-line"><ShieldCheck size={17}/>  {t("Unknowns stay visible")}</span></div><div className="small-disclosure"><Info size={16}/><p>{t("Crop numbers and checks are synthetic software fixtures. Archived NASA POWER context is available separately; reviewed local profiles are still needed.")}</p></div></div></aside></form>
        </>}

        {view === 'results' && <>
          <div className="page-heading"><div><p className="eyebrow">{t("YOUR OPTIONS, IN PERSPECTIVE")}</p><h1>{t("A clearer comparison.")}</h1><p>{applied.area}  {t("ha · Plant")} {dateLabel(applied.plantingDate, language)}  {t("· Ready for rice by")} {dateLabel(applied.riceDeadline, language)}</p></div><div className="heading-actions"><button className="button secondary" onClick={() => { setInputs({ ...applied }); go('planner'); }}><SlidersHorizontal size={16}/>  {t("Adjust inputs")}</button><button className="button primary" onClick={save}><Bookmark size={16}/>  {t("Save comparison")}</button></div></div>
          <div className="comparison-banner"><span className="round-icon"><Droplets size={22}/></span><div><strong>{t("Your priority:")} {t(priorities.find(p => p.id === applied.priority)?.label ?? '')}</strong><p>{t(applied.priority === 'soil_care' ? 'Read qualitative rotation considerations. This demo does not assign a soil-health score.' : 'Review the constraints first, then compare the options that fit. These results are illustrative.')}</p></div><span className="simulation-tag">{t(applied.simulation ? 'Simulated outcomes' : 'Yield estimates off')}</span></div>
          <div className="timeline"><div className="timeline-step"><span className="timeline-dot complete"><Check size={13}/></span><small>{t("PREVIOUS CROP")}</small><strong>{t("Rice harvested")}</strong><span>{t("Example crop history")}</span></div><div className="timeline-step"><span className="timeline-dot current"><Sprout size={14}/></span><small>{t("NEXT PLANTING")}</small><strong>{dateLabel(applied.plantingDate, language)}</strong><span>{t("Rice or rotation crop")}</span></div><div className="timeline-step"><span className="timeline-dot"><CalendarDays size={14}/></span><small>{t("YOUR DEADLINE")}</small><strong>{dateLabel(applied.riceDeadline, language)}</strong><span>{t("Field ready for rice again")}</span></div></div>
          <div className="comparison-grid">{results.map(crop => <article className={`result-card ${crop.id}`} key={crop.id}><div className="result-card-top"><span className={`crop-glyph ${crop.id}`}>{crop.id === 'rice' ? <Wheat size={32}/> : <Sprout size={32}/>}</span><Status result={crop}/></div><p className="overline">{t(crop.kind)}</p><h2>{t(crop.name)} <span>{crop.localName}</span></h2><p className="result-description">{t(crop.description)}</p><div className="result-metrics"><div><span>{t("Starting cost")} <small>{t("fixture")}</small></span><strong>{php(crop.upfront)}</strong></div><div><span>{t("Field ready again")} <small>{t("fixture")}</small></span><strong>{dateLabel(crop.releaseDate, language)}</strong></div><div><span>{t("Assumed irrigation need")}</span><strong>{crop.irrigationMm} <small>{t("mm / cycle")}</small></strong></div><div><span>{t("Cycle net income")} <small>{t("simulation")}</small></span><strong>{t(crop.netIncome === null ? '—' : php(crop.netIncome))}</strong></div></div><div className="result-checks">{crop.checks.map(check => <div key={check.label} className={`check-row ${check.status}`}>{check.status === 'pass' ? <CheckCircle2 size={16}/> : check.status === 'fail' ? <X size={16}/> : <CircleHelp size={16}/>}<span>{t(check.label)}</span><small>{t(check.status === 'pass' ? 'Fits demo' : check.status === 'fail' ? 'Does not fit' : 'Confirm')}</small></div>)}</div><button className="button secondary full-button" onClick={() => setDetail(crop.id)}>{t("See reasons & assumptions")} <ArrowUpRight size={16}/></button></article>)}</div>
          {!results.some(r => r.feasibility === 'feasible') && <div className="no-winner"><CircleHelp size={22}/><div><strong>{t("No confirmed fit yet—and that’s useful to know.")}</strong><p>{t("Review the failed checks and confirm missing information. The demo will not choose a winner while those constraints remain.")}</p></div></div>}
          {applied.simulation && <section className="finance-panel"><div><p className="overline">{t("TRY A FINANCIAL WHAT-IF")}</p><h2>{t("What if the selling price changes?")}</h2><p>{t("Only the money calculation changes. Harvest quantities remain fictional and fixed.")}</p></div><div className="price-fields">{results.map(crop => <label key={crop.id}>{t(crop.name)}  {t("price")} <span className="input-unit"><span>{t("₱")}</span><input aria-label={t('{crop} selling price', { crop: crop.name })} type="number" min="0" step="1" value={crop.price} onChange={e => { const n = Number(e.target.value); if (Number.isFinite(n) && n >= 0) setApplied(p => ({ ...p, [crop.id === 'rice' ? 'ricePrice' : 'mungbeanPrice']: n })); }}/><span>/ kg</span></span></label>)}</div></section>}
          <div className="comparison-footer"><span><Info size={15}/>  {t("Demo rules and money scenarios are not validated farm recommendations.")}</span><button className="text-button" onClick={download}><Download size={15}/>  {t("Download demo JSON")}</button></div>
        </>}

        {view === 'history' && <>
          <div className="page-heading"><div><p className="eyebrow">{t("ROOM TO REFLECT")}</p><h1>{t("Your saved comparisons.")}</h1><p>{t("Revisit an example without changing the inputs you saved.")}</p></div>{saved.length > 0 && <button className="button secondary" onClick={clearSaved}>{t("Clear demo history")}</button>}</div>
          <div className="session-notice"><Info size={17}/><p>{t("Demo history stays in this tab’s browser session. It is not an account or a production farm record.")}</p></div>
          {saved.length === 0 ? <div className="empty-state"><span><Bookmark size={34}/></span><h2>{t("A little space for your next idea.")}</h2><p>{t("Compare your planting options, then save a scenario to come back to it here.")}</p><button className="button primary" onClick={() => go('planner')}>{t("Create a comparison")} <ArrowRight size={17}/></button></div> : <div className="history-list">{saved.map((plan, index) => <article className="history-card" key={plan.id}><span className="history-icon"><Sprout size={22}/></span><div><p className="overline">{t("SYNTHETIC DEMO ·")} {t(plan.inputs.simulation ? 'SIMULATION ENABLED' : 'YIELD ESTIMATES OFF')}</p><h3>{t("Maligaya field · comparison")} {saved.length - index}</h3><p>{dateLabel(plan.inputs.plantingDate, language)} · {t(priorities.find(p => p.id === plan.inputs.priority)?.label ?? '')} · {php(plan.inputs.budget)}  {t("starting budget")}</p></div><button className="button secondary" onClick={() => { setApplied({ ...plan.inputs }); setInputs({ ...plan.inputs }); go('results'); }}>{t("Open")} <ArrowUpRight size={16}/></button></article>)}</div>}
        </>}

        {view === 'team' && <section className="team-page" aria-labelledby="team-title">
          <div className="team-heading"><span className="team-kicker"><Sprout size={16}/>{t('AniNow Klima')}</span><h1 id="team-title">{t('Our team')}</h1></div>
          <div className="team-grid">{team.map(member => <article className="team-card" key={member.name}><img src={`/images/team/${member.photo}`} alt={member.name} loading="lazy"/><h2>{member.name}</h2></article>)}</div>
        </section>}

        {view === 'sources' && <>
          <div className="page-heading"><div><p className="eyebrow">{t("TRANSPARENT BY DESIGN")}</p><h1>{t("The evidence behind the idea.")}</h1><p>{t("What the challenge asks, what this prototype does, and what comes next.")}</p></div><a className="button secondary" href={sourceLinks[0].url} target="_blank" rel="noreferrer">{t("Official challenge")} <ExternalLink size={16}/></a></div>
          <section className="challenge-intro"><span className="round-icon"><Satellite size={28}/></span><div><p className="overline">NASA SPACE APPS 2026</p><h2>Field Shift: Adapting Farms with NASA Data</h2><p>{t("Explore crop-rotation strategies through Earth observations, local soil knowledge, crop characteristics, and the farmer’s own priorities.")}</p></div></section>
          <div className="guideline-grid"><section className="plain-card"><span className="overline">{t("HOW WE APPLY THE BRIEF")}</span><h2>{t("Four parts of a useful decision.")}</h2>{['Environmental context with a clear source and date', 'Local soil and drainage information, with unknowns allowed', 'Crop history, requirements and the next planting window', 'Farmer priorities plus practical budget and buyer constraints'].map((s, i) => <div className="guideline-row" key={s}><span>{String(i + 1).padStart(2, '0')}</span><p>{t(s)}</p></div>)}</section><section className="plain-card prototype-scope"><span className="overline">{t("THIS VERSION")}</span><h2>{t("A working interaction prototype.")}</h2><p>{t("Field inputs, constraint checks, illustrative calculations, comparison details, and session saves work in your browser.")}</p><p>{t("The dashboard temperature and precipitation cards use an archived NASA POWER sample. Crop durations, water needs, yields, prices, and costs are synthetic fixtures. No live feed, trained model, published pilot, or expert-approved crop profile is connected.")}</p><p>{t("AI assisted the implementation and documentation. Cite tools and contributions in the final submission, and verify the current event’s exact disclosure rules.")}</p></section></div>
          <div className="section-heading"><div><span className="section-index">{t("↗")}</span><h2>{t("Official guidance & planned sources")}</h2></div></div><div className="sources-list">{sourceLinks.map(source => <a href={source.url} target="_blank" rel="noreferrer" className="source-card" key={source.name}><div><span className="overline">{t(source.type)}</span><h3>{t(source.name)} <ArrowUpRight size={17}/></h3><p>{t(source.description)}</p></div></a>)}</div>
          <div className="source-disclaimer"><ShieldCheck size={19}/><p>{t("Independent prototype. NASA does not endorse this app. Keep citations and dataset permissions with the project; confirm final submission requirements before claiming eligibility.")}</p></div>
        </>}
        <footer className="app-footer"><span><span className="footer-leaf"><Sprout size={14}/></span>  {t("A little clarity for what grows next.")}</span><span>{t("Historical context + demo scenarios · Not farm advice")}</span></footer>
      </main>
    </div>
    {toast && <div className="toast" role="status"><CheckCircle2 size={18}/>{t(toast)}</div>}
    {selected && <div className="modal-backdrop" onClick={() => setDetail(null)}><section ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="detail-title" className="detail-dialog" onClick={e => e.stopPropagation()}><div className="dialog-header"><div><p className="overline">{t("REASONS & ASSUMPTIONS")}</p><h2 id="detail-title">{t(selected.name)}{t(", in context.")}</h2></div><button autoFocus className="icon-button" onClick={() => setDetail(null)} aria-label={t("Close crop details")}><X size={21}/></button></div><Status result={selected}/><p className="dialog-description">{t(selected.rotationNote)}</p><div className="dialog-checks">{selected.checks.map(c => <div key={c.label}><span className={`check-bullet ${c.status}`}>{c.status === 'pass' ? <Check size={15}/> : c.status === 'fail' ? <X size={15}/> : <CircleHelp size={15}/>}</span><div><strong>{t(c.label)}</strong><p>{t(c.detail)}</p></div></div>)}</div>{applied.simulation && <div className="dialog-finance"><div><span>{t("Fictional marketable harvest")}</span><strong>{selected.yieldKg?.toLocaleString()} kg</strong></div><div><span>{t("Assumed revenue")}</span><strong>{php(selected.revenue!)}</strong></div><div><span>{t("Complete demo cycle costs")}</span><strong>{php(selected.totalCost)}</strong></div><div><span>{t("Illustrative net income")}</span><strong>{php(selected.netIncome!)}</strong></div><small>{t("Upfront cost is part of the total, not added again. This simplified fixture assumes the full harvest and all costs are within the comparison period.")}</small></div>}<div className="small-disclosure"><Info size={16}/><p>{t("Every number here is a software fixture, not an observation or crop recommendation. Real use needs reviewed local evidence.")}</p></div><button className="button primary full-button" onClick={() => { setDetail(null); setInputs({ ...applied }); go('planner'); }}>{t("Adjust the scenario")} <ArrowRight size={16}/></button></section></div>}
  </div>;
}
