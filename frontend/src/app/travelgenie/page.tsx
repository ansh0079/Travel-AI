import TravelGeniePanel from '@/components/TravelGeniePanel';

export const metadata = {
  title: 'TravelGenie - 6-Agent Travel Intelligence',
  description: 'Get weather, route, flights, restaurants, attractions and events for any trip in one shot.',
};

export default function TravelGeniePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-violet-50 via-indigo-50 to-blue-50 py-12 px-4">
      <div className="max-w-4xl mx-auto mb-10 text-center">
        <span className="inline-block px-4 py-1.5 rounded-full bg-violet-100 text-violet-700 text-sm font-medium mb-4">
          Multi-Agent System
        </span>
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
          TravelGenie Intelligence
        </h1>
        <p className="text-gray-500 max-w-xl mx-auto">
          Six specialized AI agents work in parallel — weather, route, flights, food, attractions and events — all in one request.
        </p>
      </div>
      <TravelGeniePanel />
      <div className="text-center mt-8">
        <a href="/" className="text-sm text-gray-400 hover:text-gray-600 transition-colors">
          ← Back to Trip Planner
        </a>
      </div>
    </main>
  );
}
