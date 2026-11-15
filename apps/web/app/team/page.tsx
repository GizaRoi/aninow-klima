'use client';

import Link from 'next/link';
import { ArrowLeft, MapPin, Sprout } from 'lucide-react';
import { useLanguagePreference } from '../../lib/language';
import { messages } from '../../lib/messages';
import { SiteFooter, SiteHeader } from '../components/site-shell';

const team = [
  { name: 'Romano Franco Huraño', photo: 'romano-franco-hurano-updated.webp' },
  { name: 'Christian Paul Godilano', photo: 'christian-paul-godilano-updated.webp' },
  { name: 'Roimarc Bilbao', photo: 'roimarc-bilbao-updated.webp' },
  { name: 'Yuan Yancey Labay', photo: 'yuan-yancey-labay-updated.webp' },
];

export default function TeamPage() {
  const { language, setLanguage, ready } = useLanguagePreference();
  const m = messages(language);
  return <div id="top" className="app-shell">
    <a className="skip-link" href="#team">{m.navTeam}</a>
    <SiteHeader language={language} ready={ready} onLanguageChange={setLanguage} activePage="team"/>
    <main className="team-page" id="team" aria-labelledby="team-title">
      <div className="team-heading"><div><span className="eyebrow"><Sprout size={16}/>AniNow Klima</span><h1 id="team-title">{m.navTeam}</h1></div><Link className="button team-back" href="/#planner"><ArrowLeft size={16}/>{m.backToPlanner}</Link></div>
      <div className="team-intro"><p>{m.teamDescription}</p><div className="team-location"><MapPin size={24} aria-hidden="true"/><p>{m.teamLocation}</p></div></div>
      <div className="team-grid">{team.map(member => <div className="team-card" key={member.photo}><img src={`/images/team/${member.photo}`} alt={member.name} loading="eager"/></div>)}</div>
    </main>
    <SiteFooter language={language}/>
  </div>;
}
