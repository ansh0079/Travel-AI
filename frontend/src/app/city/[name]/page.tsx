import { Suspense } from 'react';
import CityDetailsClient from './CityDetailsClient';

// Pre-generate the most common AI-recommended cities at build time
export function generateStaticParams() {
  return [
    { name: 'paris' }, { name: 'tokyo' }, { name: 'london' }, { name: 'bali' },
    { name: 'new-york' }, { name: 'new%20york' }, { name: 'New%20York' },
    { name: 'dubai' }, { name: 'singapore' }, { name: 'bangkok' },
    { name: 'rome' }, { name: 'barcelona' }, { name: 'sydney' },
    { name: 'amsterdam' }, { name: 'istanbul' }, { name: 'lisbon' },
    { name: 'prague' }, { name: 'vienna' }, { name: 'athens' },
    { name: 'kyoto' }, { name: 'osaka' }, { name: 'seoul' },
    { name: 'hong-kong' }, { name: 'Hong%20Kong' }, { name: 'miami' },
    { name: 'cancun' }, { name: 'buenos-aires' }, { name: 'rio-de-janeiro' },
    { name: 'cape-town' }, { name: 'marrakech' }, { name: 'cairo' },
    { name: 'milan' }, { name: 'florence' }, { name: 'venice' },
    { name: 'madrid' }, { name: 'edinburgh' }, { name: 'dublin' },
    { name: 'zurich' }, { name: 'berlin' }, { name: 'munich' },
    { name: 'toronto' }, { name: 'vancouver' }, { name: 'montreal' },
    { name: 'mexico-city' }, { name: 'phuket' }, { name: 'chiang-mai' },
    { name: 'maldives' }, { name: 'santorini' }, { name: 'mykonos' },
  ];
}

// Allow any city not in the static list (works in dev; graceful 404 in prod for unknown cities)
export const dynamicParams = true;

function Loading() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading city details...</p>
      </div>
    </div>
  );
}

export default function CityPage() {
  return (
    <Suspense fallback={<Loading />}>
      <CityDetailsClient />
    </Suspense>
  );
}
