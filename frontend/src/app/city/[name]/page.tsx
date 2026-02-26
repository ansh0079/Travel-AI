import { Suspense } from 'react';
import CityDetailsClient from './CityDetailsClient';

// Required for static export with dynamic routes
export function generateStaticParams() {
  return [
    { name: 'paris' },
    { name: 'tokyo' },
    { name: 'london' },
    { name: 'new-york' },
    { name: 'dubai' },
    { name: 'singapore' },
    { name: 'bangkok' },
    { name: 'rome' },
    { name: 'barcelona' },
    { name: 'sydney' },
  ];
}

// Disable dynamic params - only pre-generated cities work
export const dynamicParams = false;

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
