'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Cloud, Route, Plane, UtensilsCrossed, Landmark, Ticket,
  Loader2, MapPin, Calendar, ArrowRight, AlertCircle, Wind,
  Droplets, Thermometer, Clock, Fuel, Star, ExternalLink
} from 'lucide-react';
import { api, TravelGenieResult } from '@/services/api';

type TabId = 'weather' | 'route' | 'flights' | 'restaurants' | 'attractions' | 'events';

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'weather',     label: 'Weather',     icon: <Cloud className="w-4 h-4" /> },
  { id: 'route',       label: 'Route',       icon: <Route className="w-4 h-4" /> },
  { id: 'flights',     label: 'Flights',     icon: <Plane className="w-4 h-4" /> },
  { id: 'restaurants', label: 'Restaurants', icon: <UtensilsCrossed className="w-4 h-4" /> },
  { id: 'attractions', label: 'Attractions', icon: <Landmark className="w-4 h-4" /> },
  { id: 'events',      label: 'Events',      icon: <Ticket className="w-4 h-4" /> },
];

function StarRating({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-1 text-amber-500 text-sm">
      <Star className="w-3.5 h-3.5 fill-current" />
      {rating > 0 ? rating.toFixed(1) : 'N/A'}
    </span>
  );
}

function AgentBadge({ used }: { used: boolean }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${used ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400'}`}>
      {used ? 'Active' : 'No data'}
    </span>
  );
}

export default function TravelGeniePanel() {
  const [form, setForm] = useState({ source: '', destination: '', travel_date: '', return_date: '' });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TravelGenieResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('weather');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.source || !form.destination || !form.travel_date) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.travelGenieCompleteInfo(
        form.source,
        form.destination,
        form.travel_date,
        form.return_date || undefined
      );
      setResult(data);
      // Default to first tab that has data
      const firstActive = TABS.find(t => data.agents_used.includes(t.id));
      if (firstActive) setActiveTab(firstActive.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Form */}
      <div className="bg-white rounded-3xl shadow-2xl overflow-hidden">
        <div className="bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-5">
          <h2 className="text-white text-xl font-bold">6-Agent Travel Intelligence</h2>
          <p className="text-white/70 text-sm mt-1">Weather · Route · Flights · Food · Attractions · Events</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="From (e.g. London)"
              value={form.source}
              onChange={e => setForm(f => ({ ...f, source: e.target.value }))}
              className="w-full pl-9 pr-3 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              required
            />
          </div>

          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-violet-500" />
            <input
              type="text"
              placeholder="To (e.g. Paris)"
              value={form.destination}
              onChange={e => setForm(f => ({ ...f, destination: e.target.value }))}
              className="w-full pl-9 pr-3 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              required
            />
          </div>

          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="date"
              value={form.travel_date}
              onChange={e => setForm(f => ({ ...f, travel_date: e.target.value }))}
              className="w-full pl-9 pr-3 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              required
            />
          </div>

          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="date"
              value={form.return_date}
              onChange={e => setForm(f => ({ ...f, return_date: e.target.value }))}
              className="w-full pl-9 pr-3 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              placeholder="Return date (optional — enables flights)"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 pointer-events-none">optional</span>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="sm:col-span-2 flex items-center justify-center gap-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-colors"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Running all agents…</>
            ) : (
              <><ArrowRight className="w-4 h-4" /> Get Full Travel Intel</>
            )}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 flex items-center gap-3 bg-red-50 border border-red-200 rounded-2xl px-5 py-4 text-red-700"
        >
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span className="text-sm">{error}</span>
        </motion.div>
      )}

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 bg-white rounded-3xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between flex-wrap gap-2">
              <div>
                <h3 className="font-bold text-gray-900 text-lg">
                  {result.source} <ArrowRight className="inline w-4 h-4 text-gray-400" /> {result.destination}
                </h3>
                <p className="text-sm text-gray-500">{result.travel_date}{result.return_date ? ` → ${result.return_date}` : ''}</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {TABS.map(t => (
                  <div key={t.id} className="flex items-center gap-1 text-xs">
                    <span className="text-gray-500">{t.label}:</span>
                    <AgentBadge used={result.agents_used.includes(t.id)} />
                  </div>
                ))}
              </div>
            </div>

            {/* Tabs */}
            <div className="flex overflow-x-auto border-b border-gray-100">
              {TABS.map(tab => {
                const hasData = result.agents_used.includes(tab.id);
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    disabled={!hasData}
                    className={`flex items-center gap-2 px-5 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-violet-600 text-violet-600'
                        : hasData
                        ? 'border-transparent text-gray-500 hover:text-gray-800'
                        : 'border-transparent text-gray-300 cursor-not-allowed'
                    }`}
                  >
                    {tab.icon} {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Tab content */}
            <div className="p-6">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                >
                  {activeTab === 'weather' && result.data.weather && (
                    <WeatherTab data={result.data.weather} />
                  )}
                  {activeTab === 'route' && result.data.route && (
                    <RouteTab data={result.data.route} />
                  )}
                  {activeTab === 'flights' && (
                    <FlightsTab data={result.data.flights} />
                  )}
                  {activeTab === 'restaurants' && result.data.restaurants && (
                    <RestaurantsTab data={result.data.restaurants} />
                  )}
                  {activeTab === 'attractions' && result.data.attractions && (
                    <AttractionsTab data={result.data.attractions} />
                  )}
                  {activeTab === 'events' && result.data.events && (
                    <EventsTab data={result.data.events} />
                  )}
                </motion.div>
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Tab Components ────────────────────────────────────────────────────────────

function WeatherTab({ data }: { data: NonNullable<TravelGenieResult['data']['weather']> }) {
  if (data.error) return <ErrorCard message={data.error} />;
  return (
    <div className="space-y-4">
      <p className="text-gray-600 text-sm">{data.summary}</p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard icon={<Thermometer className="w-5 h-5 text-orange-500" />} label="Temperature" value={data.temperature} />
        <StatCard icon={<Cloud className="w-5 h-5 text-blue-400" />} label="Condition" value={data.condition} />
        <StatCard icon={<Wind className="w-5 h-5 text-teal-500" />} label="Wind" value={data.wind_speed} />
        <StatCard icon={<Droplets className="w-5 h-5 text-blue-500" />} label="Humidity" value={data.humidity} />
      </div>
    </div>
  );
}

function RouteTab({ data }: { data: NonNullable<TravelGenieResult['data']['route']> }) {
  if (data.error) return <ErrorCard message={data.error} />;
  return (
    <div className="space-y-4">
      <p className="text-gray-600 text-sm">{data.summary}</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <StatCard icon={<Route className="w-5 h-5 text-violet-500" />} label="Distance" value={`${data.distance_km} km`} sub={`${data.distance_miles} miles`} />
        <StatCard icon={<Clock className="w-5 h-5 text-indigo-500" />} label="Duration" value={`${data.duration_hours}h`} sub={`${data.duration_minutes} min`} />
        <StatCard icon={<Fuel className="w-5 h-5 text-amber-500" />} label="Fuel Est." value={`${data.fuel_estimate_liters}L`} />
      </div>
      {data.warnings && data.warnings.length > 0 && (
        <div className="text-xs text-amber-600 bg-amber-50 rounded-lg px-4 py-2">{data.warnings.join(' · ')}</div>
      )}
      <p className="text-xs text-gray-400">Provider: {data.provider}</p>
    </div>
  );
}

function FlightsTab({ data }: { data: TravelGenieResult['data']['flights'] }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        <Plane className="w-10 h-10 mx-auto mb-3 opacity-30" />
        <p className="text-sm">Add a return date to search for flights.</p>
      </div>
    );
  }
  const first = data[0] as any;
  if (first?.error) return <ErrorCard message={first.error} />;
  return (
    <div className="space-y-3">
      {data.map((flight, i) => (
        <div key={i} className="border border-gray-100 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="font-bold text-violet-600 text-lg">{flight.price} {flight.currency}</span>
            <span className="text-xs text-gray-400">{flight.segments.length} segment{flight.segments.length > 1 ? 's' : ''}</span>
          </div>
          <div className="space-y-2">
            {flight.segments.map((seg, j) => (
              <div key={j} className="flex items-center gap-3 text-sm text-gray-600">
                <span className="font-mono font-semibold text-gray-800">{seg.from_airport}</span>
                <ArrowRight className="w-3 h-3 text-gray-300" />
                <span className="font-mono font-semibold text-gray-800">{seg.to_airport}</span>
                <span className="text-gray-400">·</span>
                <span>{seg.carrier_code}</span>
                <span className="text-gray-400">·</span>
                <span>{seg.duration}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function RestaurantsTab({ data }: { data: NonNullable<TravelGenieResult['data']['restaurants']> }) {
  if (data.error) return <ErrorCard message={data.error} />;
  return (
    <div className="space-y-3">
      {data.top_restaurants.map((r, i) => (
        <div key={i} className="flex items-start gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors">
          <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center shrink-0">
            <UtensilsCrossed className="w-4 h-4 text-orange-500" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-medium text-gray-800 text-sm truncate">{r.name}</p>
              <StarRating rating={r.rating} />
            </div>
            <p className="text-xs text-gray-400 truncate">{r.address}</p>
            <div className="flex gap-1 mt-1 flex-wrap">
              {r.types?.map((t, j) => (
                <span key={j} className="text-xs bg-orange-50 text-orange-600 px-2 py-0.5 rounded-full">{t}</span>
              ))}
            </div>
          </div>
        </div>
      ))}
      <p className="text-xs text-gray-400 pt-1">Provider: {data.provider} · {data.total_found} found</p>
    </div>
  );
}

function AttractionsTab({ data }: { data: NonNullable<TravelGenieResult['data']['attractions']> }) {
  if ((data as any).error) return <ErrorCard message={(data as any).error} />;
  const items = (data as any).top_attractions || [];
  return (
    <div className="space-y-3">
      {items.map((a: any, i: number) => (
        <div key={i} className="flex items-start gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors">
          <div className="w-8 h-8 rounded-full bg-violet-100 flex items-center justify-center shrink-0">
            <Landmark className="w-4 h-4 text-violet-500" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-medium text-gray-800 text-sm truncate">{a.name}</p>
              {a.rating > 0 && <StarRating rating={a.rating} />}
            </div>
            <p className="text-xs text-gray-400 truncate">{a.address}</p>
            {a.category && (
              <span className="text-xs bg-violet-50 text-violet-600 px-2 py-0.5 rounded-full mt-1 inline-block">{a.category}</span>
            )}
          </div>
        </div>
      ))}
      {items.length === 0 && <p className="text-gray-400 text-sm text-center py-6">No attractions found.</p>}
    </div>
  );
}

function EventsTab({ data }: { data: NonNullable<TravelGenieResult['data']['events']> }) {
  if ((data as any).error) return <ErrorCard message={(data as any).error} />;
  const events = data.events || [];
  return (
    <div className="space-y-3">
      {events.length === 0 && (
        <p className="text-gray-400 text-sm text-center py-6">No events found for this period.</p>
      )}
      {events.map((ev, i) => (
        <div key={i} className="flex items-start gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors">
          <div className="w-8 h-8 rounded-full bg-pink-100 flex items-center justify-center shrink-0">
            <Ticket className="w-4 h-4 text-pink-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-800 text-sm truncate">{ev.name}</p>
            <p className="text-xs text-gray-500">{ev.venue} · {ev.date}</p>
            {ev.category && (
              <span className="text-xs bg-pink-50 text-pink-600 px-2 py-0.5 rounded-full mt-1 inline-block">{ev.category}</span>
            )}
          </div>
          {ev.ticket_url && (
            <a href={ev.ticket_url} target="_blank" rel="noopener noreferrer" className="text-violet-500 hover:text-violet-700 shrink-0">
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Shared sub-components ─────────────────────────────────────────────────────

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4 flex flex-col gap-2">
      {icon}
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="font-bold text-gray-800">{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 text-red-600 text-sm">
      <AlertCircle className="w-4 h-4 shrink-0" />
      {message}
    </div>
  );
}
