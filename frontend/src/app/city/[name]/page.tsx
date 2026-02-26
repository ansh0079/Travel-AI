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

export default function CityPage() {
  return <CityDetailsClient />;
}
