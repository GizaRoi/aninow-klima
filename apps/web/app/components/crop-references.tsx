import React from 'react';
import type { ModelCrop } from '../../lib/model';
import { referencesForCrop, type ModelReference } from '../../lib/model-references';

function Reference({ source }: { source: ModelReference }) {
  return <>
    {source.authors}{source.authors.endsWith('.') ? '' : '.'} ({source.date}).{' '}
    {source.italicTitle ? <cite>{source.title}</cite> : source.title}
    {source.description && <> [{source.description}]</>}
    {source.series && <> ({source.series})</>}.{' '}
    {source.journal && <><cite>{source.journal.title}, {source.journal.volume}</cite>, Article {source.journal.article}.{' '}</>}
    {source.publisher && <>{source.publisher}.{' '}</>}
    {source.website && <>{source.website}.{' '}</>}
    {source.retrieved && <>Retrieved {source.retrieved}, from{' '}</>}
    <a href={source.url} target="_blank" rel="noopener noreferrer">{source.url}</a>
  </>;
}

export function CropReferences({ result, waterSource, heading, unmatchedLabel = 'Source information from the model', notesLabel = 'Model assumptions & source notes' }: {
  result: Pick<ModelCrop, 'limits_source' | 'cycle_source' | 'guide_check'>;
  waterSource: string;
  heading: string;
  unmatchedLabel?: string;
  notesLabel?: string;
}) {
  const { references, unmatched } = referencesForCrop(result, waterSource);
  return <section className="crop-references">
    <h4>{heading}</h4>
    {references.length > 0 && <ul className="apa-references" role="list">
      {references.map(source => <li key={source.id}><Reference source={source}/></li>)}
    </ul>}
    {unmatched.map(raw => <p className="unmatched-source" key={raw}><strong>{unmatchedLabel}:</strong> {raw}</p>)}
    <details className="model-source-notes"><summary>{notesLabel}</summary><div>{[...new Set([result.limits_source, result.cycle_source, waterSource].filter(Boolean))].map(note => <p key={note}>{note}</p>)}</div></details>
  </section>;
}
