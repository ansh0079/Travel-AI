import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Link from 'next/link';
import './globals.css';
import ErrorBoundary from '@/components/ErrorBoundary';

const inter = Inter({ 
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'),
  title: 'TravelAI - Your AI-Powered Travel Companion',
  description: 'Discover your next dream adventure with AI-powered travel planning. Get personalized itineraries, real-time insights, and smart recommendations.',
  keywords: ['travel', 'AI', 'itinerary', 'vacation', 'destinations', 'trip planning'],
  authors: [{ name: 'TravelAI' }],
  openGraph: {
    title: 'TravelAI - Your AI-Powered Travel Companion',
    description: 'Discover your next dream adventure with AI-powered travel planning',
    type: 'website',
  },
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const year = new Date().getFullYear();

  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-[#0a0a19] text-white`} suppressHydrationWarning>
        <ErrorBoundary>
          <div className="min-h-screen flex flex-col">
            <div className="flex-1">{children}</div>
            <footer className="border-t border-white/10 py-4 px-4">
              <div className="max-w-6xl mx-auto flex items-center justify-between text-xs text-gray-400">
                <span>(c) {year} TravelAI</span>
                <div className="flex items-center gap-4">
                  <Link href="/privacy" className="hover:text-white transition-colors">
                    Privacy
                  </Link>
                  <Link href="/terms" className="hover:text-white transition-colors">
                    Terms
                  </Link>
                </div>
              </div>
            </footer>
          </div>
        </ErrorBoundary>
      </body>
    </html>
  );
}
