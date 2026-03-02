import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import ErrorBoundary from '@/components/ErrorBoundary';

const inter = Inter({ 
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata: Metadata = {
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
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-[#0a0a19] text-white`} suppressHydrationWarning>
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
      </body>
    </html>
  );
}
