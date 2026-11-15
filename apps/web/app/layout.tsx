import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AniNow Klima — Your next planting',
  description: 'Explore what to plant after rice. A frontend preview with sample crop comparisons for Muñoz, Nueva Ecija.',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" data-scroll-behavior="smooth"><body>{children}</body></html>;
}
