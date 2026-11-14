'use client';

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { Languages } from 'lucide-react';
import { translate, type Language, type TranslationValues } from './translations';

type LanguageContext = { language: Language; setLanguage: (language: Language) => void; t: (text: string, values?: TranslationValues) => string };
const Context = createContext<LanguageContext | null>(null);
const storageKey = 'aninow-language-v1';

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, updateLanguage] = useState<Language>('en');
  useEffect(() => {
    try { if (localStorage.getItem(storageKey) === 'tl') updateLanguage('tl'); } catch { /* Language switching still works without storage. */ }
  }, []);
  useEffect(() => {
    document.documentElement.lang = language;
    document.title = language === 'tl' ? 'AniNow Klima — Planuhin ang susunod na tanim' : 'AniNow Klima — Plan your next planting';
  }, [language]);
  const setLanguage = useCallback((next: Language) => {
    updateLanguage(next);
    try { localStorage.setItem(storageKey, next); } catch { /* Storage is optional. */ }
  }, []);
  const t = useCallback((text: string, values?: TranslationValues) => translate(text, language, values), [language]);
  return <Context.Provider value={{ language, setLanguage, t }}>{children}</Context.Provider>;
}

export function useLanguage() {
  const context = useContext(Context);
  if (!context) throw new Error('LanguageProvider is required.');
  return context;
}

export function LanguageSwitch() {
  const { language, setLanguage } = useLanguage();
  return <div className="language-bar">
    <span className="language-label-visible"><Languages size={20} aria-hidden="true"/><span><span className="language-label-en">Language / </span>Wika</span></span>
    <div className="language-buttons" role="group" aria-label="Language / Wika">
      <button type="button" lang="en" aria-pressed={language === 'en'} onClick={() => setLanguage('en')}>English</button>
      <button type="button" lang="tl" aria-pressed={language === 'tl'} onClick={() => setLanguage('tl')}>Tagalog</button>
    </div>
  </div>;
}
