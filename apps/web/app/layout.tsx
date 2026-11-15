import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AniNow Klima — Your next planting',
  description: 'Compare planting options with historical weather, field conditions, and the AniNow Klima rules model.',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" data-scroll-behavior="smooth"><body>{children}</body></html>;
}
