'use client';

import { useEffect, useState } from 'react';
import type { Language } from './preview';

export function useLanguagePreference() {
  const [language, setLanguage] = useState<Language>('en');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('aninow-tool-language');
      if (stored === 'en' || stored === 'tl') setLanguage(stored);
    } catch { /* Storage is optional. */ }
    setReady(true);
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
    if (!ready) return;
    try { localStorage.setItem('aninow-tool-language', language); } catch { /* Storage is optional. */ }
  }, [language, ready]);

  return { language, setLanguage, ready };
}
