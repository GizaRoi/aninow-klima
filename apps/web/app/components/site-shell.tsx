'use client';

import Link from 'next/link';
import { useId, useState } from 'react';
import { ArrowUpRight, Menu, X } from 'lucide-react';
import { messages } from '../../lib/messages';
import type { Language } from '../../lib/preview';

export function BrandLogo() {
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  // Adapt only the dark lettering for the dark page; keep the source PNG unchanged.
  return <svg className="brand-logo" viewBox="199 414 1635 1128" role="img" aria-label="AniNow Klima" width="1635" height="1128">
    <defs>
      <filter id={`${id}-light-wordmark`} colorInterpolationFilters="sRGB"><feColorMatrix type="matrix" values="0 0 0 0 .94  0 0 0 0 .96  0 0 0 0 .89  0 0 0 1 0"/></filter>
      <clipPath id={`${id}-dark-lettering`}><rect x="0" y="1000" width="900" height="400"/><rect x="0" y="1400" width="2000" height="600"/></clipPath>
    </defs>
    <image href="/images/aninow-logo.png" width="2000" height="2000"/>
    <image href="/images/aninow-logo.png" width="2000" height="2000" clipPath={`url(#${id}-dark-lettering)`} filter={`url(#${id}-light-wordmark)`}/>
  </svg>;
}

export function SiteHeader({ language, ready, onLanguageChange, activePage = 'field' }: {
  language: Language;
  ready: boolean;
  onLanguageChange: (language: Language) => void;
  activePage?: 'field' | 'team';
}) {
  const [mobileMenu, setMobileMenu] = useState(false);
  const m = messages(language);
  function closeMenu() { setMobileMenu(false); }
  return <header className="site-header">
    <Link className="brand" href="/" aria-label="AniNow Klima"><BrandLogo/></Link>
    <nav aria-label={language === 'en' ? 'Main navigation' : 'Pangunahing menu'} className={mobileMenu ? 'nav-open' : ''}>
      <Link href="/team/" aria-current={activePage === 'team' ? 'page' : undefined} onClick={closeMenu}>{m.navTeam}</Link>
    </nav>
    <div className="header-tools"><div className="language-switch" role="group" aria-label="Language / Wika"><button disabled={!ready} aria-pressed={language === 'en'} onClick={() => onLanguageChange('en')}>English</button><button disabled={!ready} aria-pressed={language === 'tl'} onClick={() => onLanguageChange('tl')}>Tagalog</button></div><button className="menu-button" aria-label={m.menu} aria-expanded={mobileMenu} onClick={() => setMobileMenu(!mobileMenu)}>{mobileMenu ? <X/> : <Menu/>}</button></div>
  </header>;
}

export function SiteFooter({ language }: { language: Language }) {
  const m = messages(language);
  return <footer className="site-footer"><Link href="/" className="footer-brand" aria-label="AniNow Klima"><BrandLogo/></Link><p>{m.foot}</p><a href="#top">{m.backTop}<ArrowUpRight size={15}/></a></footer>;
}
