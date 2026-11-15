'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ArrowUpRight, Menu, X } from 'lucide-react';
import { messages } from '../../lib/messages';
import type { Language } from '../../lib/preview';

function BrandLogo() {
  // Crop transparent margins and show the original artwork on the light site chrome.
  return <svg className="brand-logo" viewBox="199 414 1635 1128" role="img" aria-label="AniNow Klima" width="1635" height="1128">
    <image href="/images/aninow-logo.png" width="2000" height="2000"/>
  </svg>;
}

export function SiteHeader({ language, ready, onLanguageChange, onPlan, activePage = 'field' }: {
  language: Language;
  ready: boolean;
  onLanguageChange: (language: Language) => void;
  onPlan?: () => void;
  activePage?: 'field' | 'team';
}) {
  const [mobileMenu, setMobileMenu] = useState(false);
  const m = messages(language);
  function closeMenu() { setMobileMenu(false); }
  return <header className="site-header">
    <Link className="brand" href="/" aria-label="AniNow Klima"><BrandLogo/></Link>
    <nav aria-label={language === 'en' ? 'Main navigation' : 'Pangunahing menu'} className={mobileMenu ? 'nav-open' : ''}>
      <Link href="/#top" onClick={closeMenu}>{m.navField}</Link>
      {onPlan ? <button onClick={() => { closeMenu(); onPlan(); }}>{m.navPlan}</button> : <Link href="/#planner" onClick={closeMenu}>{m.navPlan}</Link>}
      <Link className="nav-about" href="/#about" onClick={closeMenu}>{m.navAbout}<ArrowUpRight size={13}/></Link>
      <Link href="/team/" aria-current={activePage === 'team' ? 'page' : undefined} onClick={closeMenu}>{m.navTeam}</Link>
    </nav>
    <div className="header-tools"><div className="language-switch" role="group" aria-label="Language / Wika"><button disabled={!ready} aria-pressed={language === 'en'} onClick={() => onLanguageChange('en')}>English</button><button disabled={!ready} aria-pressed={language === 'tl'} onClick={() => onLanguageChange('tl')}>Tagalog</button></div><button className="menu-button" aria-label={m.menu} aria-expanded={mobileMenu} onClick={() => setMobileMenu(!mobileMenu)}>{mobileMenu ? <X/> : <Menu/>}</button></div>
  </header>;
}

export function SiteFooter({ language }: { language: Language }) {
  const m = messages(language);
  return <footer className="site-footer"><Link href="/" className="footer-brand" aria-label="AniNow Klima"><BrandLogo/></Link><p>{m.foot}</p><a href="#top">{m.backTop}<ArrowUpRight size={15}/></a></footer>;
}
