'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { messages } from '../../lib/messages';
import type { Language } from '../../lib/preview';
import { BrandLogo } from './site-shell';

export function AppIntro({ language, children }: { language: Language; children: ReactNode }) {
  const [phase, setPhase] = useState<'showing' | 'leaving' | 'done'>('showing');
  const [scrollbarSpace, setScrollbarSpace] = useState(0);
  const m = messages(language);

  useEffect(() => {
    // The fullscreen intro releases the root gutter. Reserve the same space
    // inside the page until the root gutter returns, so the fade never exposes
    // a wider layout. Measure a stable gutter, including on overlay-scrollbar browsers.
    const probe = document.createElement('div');
    probe.style.cssText = 'position:fixed;top:0;left:0;width:100px;height:100px;overflow:scroll;scrollbar-gutter:stable;visibility:hidden;pointer-events:none';
    document.body.appendChild(probe);
    setScrollbarSpace(probe.offsetWidth - probe.clientWidth);
    probe.remove();
    // The welcome sequence is independent of network readiness. The form keeps
    // its own loading/error state if Render needs longer to return the catalogue.
    const fade = window.setTimeout(() => setPhase('leaving'), 1800);
    const finish = window.setTimeout(() => setPhase('done'), 2100);
    return () => { window.clearTimeout(fade); window.clearTimeout(finish); };
  }, []);

  return <>
    {phase !== 'done' && <div className={`app-intro ${phase === 'leaving' ? 'is-leaving' : ''}`}>
      <img className="intro-landscape" src="/images/pexels-elmer0224-31391951.jpg" alt="" width="3024" height="4032" fetchPriority="high"/>
      <div className="intro-shade"/>
      <div className="intro-content">
        <BrandLogo/>
        <p className="intro-tagline" lang="en">{m.tagline}</p>
        <div className="intro-status" role="status"><span className="intro-track" aria-hidden="true"><span/></span><span>{m.openingPlanner}</span></div>
      </div>
      <span className="intro-credit">{m.photoCredit}</span>
    </div>}
    <div className="intro-page" inert={phase !== 'done'} style={{ paddingInlineEnd: phase === 'done' ? 0 : scrollbarSpace }}>{children}</div>
  </>;
}
