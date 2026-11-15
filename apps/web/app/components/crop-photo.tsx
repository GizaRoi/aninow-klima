import photos from '../../lib/crop-photos.json';
import type { Messages } from '../../lib/messages';

type Photo = { src: string; author: string; sourceUrl: string; license: string; licenseUrl: string; title: string };

export function CropPhoto({ cropId, name, m }: { cropId: string; name: string; m: Messages }) {
  const photo = (photos as Record<string, Photo>)[cropId];
  if (!photo) return null;
  return <figure className="crop-photo">
    <img src={photo.src} alt={name} width="720" height="360" loading="lazy" decoding="async"/>
    <figcaption><a href={photo.sourceUrl} target="_blank" rel="noreferrer" title={`${photo.title} · ${m.photoAdapted}`}>{m.photo}: {photo.author}</a><span> · </span><a href={photo.licenseUrl} target="_blank" rel="noreferrer">{photo.license}</a></figcaption>
  </figure>;
}
