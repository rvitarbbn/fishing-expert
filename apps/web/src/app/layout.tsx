import type { Metadata } from 'next';
import { Heebo } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const heebo = Heebo({
  subsets: ['hebrew', 'latin'],
  variable: '--font-heebo',
});

export const metadata: Metadata = {
  title: 'Mediterranean Shore Fishing Expert',
  description: 'יועץ דיג ז׳ירז׳ור חופי בים התיכון בישראל',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="he" dir="rtl" className={heebo.variable}>
      <body className="min-h-screen bg-gradient-to-b from-sea-light to-white font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
