'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { messages } from '../../lib/messages';
import type { Language } from '../../lib/preview';
import { BrandLogo } from './site-shell';

export function AppIntro({ language, children }: { language: Language; children: ReactNode }) {
  const [phase, setPhase] = useState<'showing' | 'leaving' | 'done'>('showing');
  const m = messages(language);

  useEffect(() => {
    // The welcome sequence is independent of network readiness. The form keeps
    // its own loading/error state if Render needs longer to return the catalogue.
    const fade = window.setTimeout(() => setPhase('leaving'), 1800);
    const finish = window.setTimeout(() => setPhase('done'), 2100);
    return () => { window.clearTimeout(fade); window.clearTimeout(finish); };
  }, []);

  return <>
    {phase !== 'done' && <div className={`app-intro ${phase === 'leaving' ? 'is-leaving' : ''}`}>
      <img className="intro-landscape" src="/images/farm-diorama.png" alt="" fetchPriority="high"/>
      <div className="intro-shade"/>
      <div className="intro-content">
        <BrandLogo/>
        <p className="intro-tagline">{m.tagline}</p>
        <div className="intro-status" role="status"><span className="intro-track" aria-hidden="true"><span/></span><span>{m.openingPlanner}</span></div>
      </div>
      <span className="intro-artwork">{m.artwork}</span>
    </div>}
    <div inert={phase !== 'done'}>{children}</div>
  </>;
}
