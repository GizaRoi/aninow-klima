'use client';

import type { Ref } from 'react';
import { CalendarDays, MapPin, Sprout } from 'lucide-react';
import { messages } from '../../lib/messages';
import { dateLabel, type FieldInputs, type Language } from '../../lib/model';

export function CalculationLoading({ inputs, language, headingRef }: {
  inputs: FieldInputs; language: Language; headingRef: Ref<HTMLHeadingElement>;
}) {
  const m = messages(language);
  return <div className="calculation-panel">
    <div className="calculation-animation" aria-hidden="true">
      <span className="calculation-ring"/><span className="calculation-ring inner"/>
      <span className="calculation-sprout"><Sprout size={38} strokeWidth={1.5}/></span>
    </div>
    <h2 id="planner-title" tabIndex={-1} ref={headingRef}>{m.calculationTitle}</h2>
    <p className="calculation-status" role="status">{m.calculating}</p>
    <div className="calculation-inputs">
      <span><MapPin size={18}/>{inputs.place}</span>
      <span><CalendarDays size={18}/>{dateLabel(inputs.harvest, language)} <span aria-hidden="true">→</span> {dateLabel(inputs.next_planting, language)}</span>
    </div>
    <div className="calculation-wait"><span className="calculation-dots" aria-hidden="true"><i/><i/><i/></span><p>{m.calculationWait}</p></div>
  </div>;
}
