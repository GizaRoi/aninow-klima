import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AniNow Klima — Plan your next planting',
  description: 'A visual prototype helping Filipino rice farmers explore their next planting. All agricultural values are synthetic demo fixtures.',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
