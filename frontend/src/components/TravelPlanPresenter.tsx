'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';

interface Source {
  title?: string;
  url?: string;
  snippet?: string;
}

interface DestData {
  weather?: { summary?: string; weather?: Record<string, unknown> };
  visa?: { summary?: string; passport?: string };
  flights?: { summary?: string; best_option?: Record<string, unknown> };
  hotels?: { summary?: string; top_picks?: any[] };
  attractions?: { summary?: string; top_picks?: any[] };
  restaurants?: {
    summary?: string;
    top_picks?: any[];
    food_scene?: { food_scene?: { must_try?: string; signature_dishes?: string[] } };
  };
  events?: { summary?: string; highlights?: any[] };
  web?: { sources?: Source[] };
}

interface DecisionEvaluation {
  destination: string;
  total_score?: number;
  personalized_total_score?: number;
  personalization_bonus?: number;
  matched_priorities?: string[];
}

interface ProactiveAlert {
  title?: string;
  message?: string;
  severity?: string;
  destination?: string;
  source?: string;
}

interface TravelPlan {
  plan_text?: string;
  destinations?: string[];
  destination_data?: Record<string, DestData>;
  preferences?: Record<string, any>;
  sources?: Source[];
  generated_at?: string;
  confidence?: string;
  is_partial?: boolean;
  completed_tasks?: number;
  total_tasks?: number;
  proactive_alerts?: ProactiveAlert[];
  decision_analysis?: {
    evaluations?: DecisionEvaluation[];
    best_destination?: string;
    best_score?: number;
    ranking_basis?: string;
  };
}

interface Props {
  plan: TravelPlan;
  sessionId?: string;
  apiBase?: string;
}

function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let listType: 'ul' | 'ol' | null = null;
  let listItems: React.ReactNode[] = [];

  const flushList = (key: number) => {
    if (!listType || !listItems.length) {
      listType = null;
      listItems = [];
      return;
    }
    if (listType === 'ul') {
      elements.push(
        <ul key={`ul-${key}`} className="mb-3 ml-6 list-disc space-y-1 text-sm text-gray-700">
          {listItems}
        </ul>
      );
    } else {
      elements.push(
        <ol key={`ol-${key}`} className="mb-3 ml-6 list-decimal space-y-1 text-sm text-gray-700">
          {listItems}
        </ol>
      );
    }
    listType = null;
    listItems = [];
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    const bulletMatch = line.match(/^(\s*)[-•*]\s(.+)/);
    const orderedMatch = line.match(/^(\s*)(\d+)\.\s(.+)/);

    if (bulletMatch) {
      if (listType === 'ol') {
        flushList(i);
      }
      listType = 'ul';
      listItems.push(
        <li key={`li-${i}`} className={bulletMatch[1].length > 0 ? 'ml-4 leading-relaxed' : 'leading-relaxed'}>
          {inlineFormat(bulletMatch[2])}
        </li>
      );
      continue;
    }

    if (orderedMatch) {
      if (listType === 'ul') {
        flushList(i);
      }
      listType = 'ol';
      listItems.push(
        <li key={`li-${i}`} className={orderedMatch[1].length > 0 ? 'ml-4 leading-relaxed' : 'leading-relaxed'}>
          {inlineFormat(orderedMatch[3])}
        </li>
      );
      continue;
    }

    flushList(i);

    if (line.startsWith('# ')) {
      elements.push(
        <h1 key={i} className="text-2xl font-bold text-gray-900 mb-3 mt-6 first:mt-0">
          {inlineFormat(line.slice(2))}
        </h1>
      );
      continue;
    }

    if (line.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="text-xl font-semibold text-gray-800 mb-2 mt-5 border-b border-gray-200 pb-1">
          {inlineFormat(line.slice(3))}
        </h2>
      );
      continue;
    }

    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="text-base font-semibold text-gray-700 mb-1.5 mt-4">
          {inlineFormat(line.slice(4))}
        </h3>
      );
      continue;
    }

    if (line.startsWith('#### ')) {
      elements.push(
        <h4 key={i} className="text-sm font-semibold text-gray-700 mb-1 mt-3">
          {inlineFormat(line.slice(5))}
        </h4>
      );
      continue;
    }

    if (line.startsWith('> ')) {
      elements.push(
        <blockquote key={i} className="border-l-4 border-blue-300 pl-4 my-2 text-sm text-gray-600 italic">
          {inlineFormat(line.slice(2))}
        </blockquote>
      );
      continue;
    }

    if (line.startsWith('---') || line.startsWith('===')) {
      elements.push(<hr key={i} className="my-4 border-gray-200" />);
      continue;
    }

    if (line.trim() === '') {
      elements.push(<div key={i} className="h-2" />);
      continue;
    }

    elements.push(
      <p key={i} className="text-sm text-gray-700 leading-relaxed mb-1">
        {inlineFormat(line)}
      </p>
    );
  }

  flushList(lines.length);

  return elements;
}

function inlineFormat(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\[.*?\]\(.*?\))/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }

    const linkMatch = part.match(/^\[(.+?)\]\((.+?)\)$/);
    if (linkMatch) {
      return (
        <a
          key={i}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 underline hover:text-blue-800"
        >
          {linkMatch[1]}
        </a>
      );
    }

    return part;
  });
}

function InfoCard({
  icon,
  title,
  children,
  color = 'blue',
}: {
  icon: string;
  title: string;
  children: React.ReactNode;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    amber: 'bg-amber-50 border-amber-200',
    purple: 'bg-purple-50 border-purple-200',
    teal: 'bg-teal-50 border-teal-200',
    rose: 'bg-rose-50 border-rose-200',
    indigo: 'bg-indigo-50 border-indigo-200',
    orange: 'bg-orange-50 border-orange-200',
  };

  return (
    <div className={`rounded-xl border p-4 ${colorMap[color] ?? colorMap.blue}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{icon}</span>
        <h3 className="font-semibold text-gray-800">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function PickList({ items, maxItems = 4 }: { items: any[]; maxItems?: number }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? items : items.slice(0, maxItems);

  return (
    <>
      <ul className="space-y-1.5">
        {shown.map((item, i) => {
          const name = item?.name || item?.title || item?.event_name || '-';
          const desc = item?.description || item?.category || item?.address || '';
          return (
            <li key={i} className="flex gap-2 text-sm">
              <span className="text-gray-400 font-bold flex-shrink-0">{i + 1}.</span>
              <span>
                <span className="font-medium text-gray-800">{name}</span>
                {desc && (
                  <span className="text-gray-500 ml-1">
                    - {desc.slice(0, 60)}
                    {desc.length > 60 ? '...' : ''}
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
      {items.length > maxItems && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-xs text-blue-600 hover:underline"
        >
          {expanded ? 'Show less' : `Show ${items.length - maxItems} more`}
        </button>
      )}
    </>
  );
}

export default function TravelPlanPresenter({ plan, sessionId, apiBase }: Props) {
  const [activeTab, setActiveTab] = useState<'overview' | 'full'>('overview');
  const [copied, setCopied] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState<'positive' | 'negative' | null>(null);
  const [feedbackSent, setFeedbackSent] = useState(false);

  const handleCopy = useCallback(async () => {
    const text = plan.plan_text || '';
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [plan.plan_text]);

  const handleDownload = useCallback(() => {
    const dest = (plan.destinations || []).join('-').replace(/\s+/g, '_') || 'travel-plan';
    const blob = new Blob([plan.plan_text || ''], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${dest}-plan.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [plan]);

  const handlePrint = useCallback(() => window.print(), []);

  const handleFeedback = useCallback(async (rating: 'positive' | 'negative') => {
    setFeedbackRating(rating);
    const base = apiBase || (typeof window !== 'undefined'
      ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1')
      : 'http://localhost:8000/api/v1');
    const dest = (plan.destinations || [])[0] || 'unknown';
    try {
      await fetch(`${base}/autonomous-agent/session/${sessionId || 'unknown'}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating, destination: dest }),
      });
    } catch {
      // Best-effort only.
    }
    setFeedbackSent(true);
  }, [apiBase, plan.destinations, sessionId]);

  if (!plan) return null;

  const destinations = plan.destinations || [];
  const prefs = plan.preferences || {};
  const destData = plan.destination_data || {};
  const allSources = plan.sources || [];
  const decisionAnalysis = plan.decision_analysis;
  const proactiveAlerts = plan.proactive_alerts || [];
  const bestEvaluation = decisionAnalysis?.evaluations?.find(
    evaluation => evaluation.destination === decisionAnalysis.best_destination
  );
  const duration = prefs.duration ? `${prefs.duration} days` : 'Flexible';
  const budget = prefs.budget_level
    ? `${prefs.budget_level.charAt(0).toUpperCase()}${prefs.budget_level.slice(1)}`
    : 'Any budget';
  const travelers = prefs.traveling_with || 'Solo';
  const interests = (prefs.interests || []).join(', ') || 'General';
  const title = plan.is_partial ? 'Building Your Travel Plan...' : 'Your Travel Plan is Ready';
  const badge = plan.confidence === 'high'
    ? 'High confidence'
    : plan.confidence === 'building'
    ? 'Live update'
    : 'Medium confidence';
  const progressLabel = plan.is_partial && plan.total_tasks
    ? `${plan.completed_tasks || 0}/${plan.total_tasks} research tasks complete`
    : null;

  // ── Passive engagement tracking ────────────────────────────────
  // Use IntersectionObserver to track how long the user views each
  // destination section.  Fires a lightweight POST to the backend
  // engagement endpoint so the learning system knows which sections
  // captured user attention.
  const destSectionRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const viewTimers = useRef<Record<string, number>>({});
  const sentEngagement = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!sessionId || destinations.length === 0) return;
    const base = apiBase || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const dest = entry.target.getAttribute('data-dest');
          if (!dest) return;
          if (entry.isIntersecting) {
            // Start timer
            if (!viewTimers.current[dest]) {
              viewTimers.current[dest] = Date.now();
            }
          } else {
            // Stop timer & send if significant
            const start = viewTimers.current[dest];
            if (start) {
              const elapsed = Date.now() - start;
              delete viewTimers.current[dest];
              if (elapsed >= 3000 && !sentEngagement.current.has(dest)) {
                sentEngagement.current.add(dest);
                // Determine most visible section based on destination data
                const data = destData[dest] || {};
                const sections = Object.keys(data).filter(k => data[k as keyof DestData]);
                const topSection = sections[0] || 'general';
                fetch(`${base}/autonomous-agent/session/${sessionId}/engagement`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    destination: dest,
                    section: topSection,
                    time_spent_ms: elapsed,
                  }),
                }).catch(() => {/* best-effort */});
              }
            }
          }
        });
      },
      { threshold: 0.3 },
    );

    // Observe all destination sections
    Object.values(destSectionRefs.current).forEach((el) => {
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, destinations.length]);

  return (
    <div className="mt-6 rounded-2xl border border-green-200 bg-gradient-to-br from-green-50 to-emerald-50 overflow-hidden shadow-lg animate-fadeIn">
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-5 text-white">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">{plan.is_partial ? '🛠️' : '🎉'}</span>
              <h2 className="text-xl font-bold">{title}</h2>
            </div>
            <p className="text-green-100 text-sm">
              {destinations.join(' · ')} · {duration} · {budget}
            </p>
            {progressLabel && (
              <p className="text-green-100 text-xs mt-1">{progressLabel}</p>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            {plan.confidence && (
              <span className="text-xs text-green-200 bg-green-700/50 px-2 py-0.5 rounded-full">
                {badge}
              </span>
            )}
            {plan.plan_text && (
              <div className="flex gap-1.5">
                <button
                  type="button"
                  onClick={handleCopy}
                  title="Copy plan as markdown"
                  className="px-2.5 py-1 rounded-lg text-xs font-medium bg-white/20 text-white hover:bg-white/30 transition-colors"
                >
                  {copied ? 'Copied' : 'Copy'}
                </button>
                <button
                  type="button"
                  onClick={handleDownload}
                  title="Download as .md file"
                  className="px-2.5 py-1 rounded-lg text-xs font-medium bg-white/20 text-white hover:bg-white/30 transition-colors"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={handlePrint}
                  title="Print plan"
                  className="px-2.5 py-1 rounded-lg text-xs font-medium bg-white/20 text-white hover:bg-white/30 transition-colors"
                >
                  Print
                </button>
                <span className="w-px h-4 bg-white/30" />
                {feedbackSent ? (
                  <span className="px-2.5 py-1 text-xs font-medium text-green-200">
                    Thanks
                  </span>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => handleFeedback('positive')}
                      disabled={feedbackSent}
                      title="This plan was helpful"
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                        feedbackRating === 'positive'
                          ? 'bg-green-500 text-white'
                          : 'bg-white/20 text-white hover:bg-green-500/50'
                      }`}
                    >
                      Like
                    </button>
                    <button
                      type="button"
                      onClick={() => handleFeedback('negative')}
                      disabled={feedbackSent}
                      title="This plan needs improvement"
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                        feedbackRating === 'negative'
                          ? 'bg-red-500 text-white'
                          : 'bg-white/20 text-white hover:bg-red-500/50'
                      }`}
                    >
                      Dislike
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
          {[
            { label: 'Destination', value: destinations.join(', ') || 'TBD' },
            { label: 'Duration', value: duration },
            { label: 'Budget', value: budget },
            { label: 'Travelling as', value: travelers },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white/10 rounded-lg p-2 text-center">
              <div className="text-xs text-green-200">{label}</div>
              <div className="text-sm font-semibold truncate">{value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex border-b border-green-200 bg-white/50">
        {(['overview', 'full'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-5 py-3 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'border-b-2 border-green-600 text-green-700'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab === 'overview' ? 'Overview' : 'Full Plan'}
          </button>
        ))}
      </div>

      <div className="p-5">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {(decisionAnalysis || proactiveAlerts.length > 0) && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {decisionAnalysis?.best_destination && (
                  <InfoCard icon="🧭" title="Best Match" color="green">
                    <p className="text-sm font-medium text-gray-800">
                      {decisionAnalysis.best_destination}
                    </p>
                    {typeof decisionAnalysis.best_score === 'number' && (
                      <p className="text-xs text-gray-500 mt-1">
                        Score: {decisionAnalysis.best_score.toFixed(2)}
                        {decisionAnalysis.ranking_basis === 'personalized' ? ' · Personalized' : ''}
                      </p>
                    )}
                    {bestEvaluation?.matched_priorities && bestEvaluation.matched_priorities.length > 0 && (
                      <p className="text-xs text-gray-500 mt-2">
                        Matched priorities: {bestEvaluation.matched_priorities.join(', ')}
                      </p>
                    )}
                  </InfoCard>
                )}

                {proactiveAlerts.length > 0 && (
                  <InfoCard icon="🔔" title="Smart Alerts" color="amber">
                    <ul className="space-y-2">
                      {proactiveAlerts.slice(0, 4).map((alert, index) => (
                        <li key={`${alert.title || 'alert'}-${index}`} className="text-sm text-gray-700">
                          <span className="font-medium">{alert.title || 'Travel alert'}</span>
                          {alert.destination ? ` · ${alert.destination}` : ''}
                          {alert.message ? <span className="block text-xs text-gray-500 mt-0.5">{alert.message}</span> : null}
                        </li>
                      ))}
                    </ul>
                  </InfoCard>
                )}
              </div>
            )}

            {destinations.map((dest) => {
              const data = destData[dest] || {};
              const foodScene = data.restaurants?.food_scene?.food_scene;

              return (
                <div
                  key={dest}
                  data-dest={dest}
                  ref={(el) => { destSectionRefs.current[dest] = el; }}
                >
                  <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                    <span>📍</span>
                    {dest}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {data.weather && (
                      <InfoCard icon="🌤️" title="Weather" color="blue">
                        <p className="text-sm text-gray-700">{data.weather.summary || 'N/A'}</p>
                      </InfoCard>
                    )}

                    {data.visa && (
                      <InfoCard icon="🛂" title="Visa & Entry" color="purple">
                        <p className="text-sm text-gray-700">{data.visa.summary || 'N/A'}</p>
                        {data.visa.passport && (
                          <p className="text-xs text-gray-500 mt-1">Passport: {data.visa.passport}</p>
                        )}
                      </InfoCard>
                    )}

                    {data.flights && (
                      <InfoCard icon="✈️" title="Getting There" color="indigo">
                        <p className="text-sm text-gray-700">{data.flights.summary || 'N/A'}</p>
                      </InfoCard>
                    )}

                    {data.hotels && (
                      <InfoCard icon="🏨" title="Where to Stay" color="teal">
                        <p className="text-sm text-gray-700 mb-2">{data.hotels.summary || 'N/A'}</p>
                        {data.hotels.top_picks && data.hotels.top_picks.length > 0 && (
                          <PickList items={data.hotels.top_picks} maxItems={3} />
                        )}
                      </InfoCard>
                    )}

                    {data.restaurants && (
                      <InfoCard icon="🍽️" title="Food & Dining" color="amber">
                        <p className="text-sm text-gray-700 mb-2">{data.restaurants.summary || 'N/A'}</p>
                        {foodScene?.must_try && (
                          <p className="text-xs text-gray-500 mb-2">Must try: {foodScene.must_try}</p>
                        )}
                        {data.restaurants.top_picks && data.restaurants.top_picks.length > 0 && (
                          <PickList items={data.restaurants.top_picks} maxItems={3} />
                        )}
                      </InfoCard>
                    )}

                    {data.attractions && (
                      <InfoCard icon="🏛️" title="Top Attractions" color="orange">
                        {data.attractions.top_picks && data.attractions.top_picks.length > 0 ? (
                          <PickList items={data.attractions.top_picks} maxItems={4} />
                        ) : (
                          <p className="text-sm text-gray-600">{data.attractions.summary || 'N/A'}</p>
                        )}
                      </InfoCard>
                    )}

                    {data.events && data.events.highlights && data.events.highlights.length > 0 && (
                      <InfoCard icon="🎭" title="Local Events" color="rose">
                        <PickList items={data.events.highlights} maxItems={3} />
                      </InfoCard>
                    )}
                  </div>

                  {data.web?.sources && data.web.sources.length > 0 && (
                    <div className="mt-3">
                      <InfoCard icon="🔗" title="Web Sources" color="green">
                        <div className="space-y-1">
                          {data.web.sources.slice(0, 4).map((src, i) => (
                            src.url ? (
                              <a
                                key={i}
                                href={src.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-start gap-1.5 text-xs text-blue-600 hover:underline"
                              >
                                <span className="text-gray-400 flex-shrink-0">↗</span>
                                <span className="truncate">{src.title || src.url}</span>
                              </a>
                            ) : null
                          ))}
                        </div>
                      </InfoCard>
                    </div>
                  )}
                </div>
              );
            })}

            {interests && interests !== 'General' && (
              <div className="bg-white/60 rounded-xl border border-gray-200 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span>🎯</span>
                  <span className="text-sm font-semibold text-gray-700">Tailored for your interests</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(prefs.interests || []).map((interest: string) => (
                    <span
                      key={interest}
                      className="px-3 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium capitalize"
                    >
                      {interest}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {allSources.length > 0 && (
              <details className="group">
                <summary className="cursor-pointer text-sm font-medium text-gray-600 hover:text-gray-900 list-none flex items-center gap-1">
                  <span className="group-open:hidden">▶</span>
                  <span className="hidden group-open:inline">▼</span>
                  All research sources ({allSources.length})
                </summary>
                <div className="mt-2 grid gap-1 pl-4">
                  {allSources.map((src, i) => (
                    src.url ? (
                      <a
                        key={i}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:underline truncate block"
                      >
                        {src.title || src.url}
                      </a>
                    ) : null
                  ))}
                </div>
              </details>
            )}
          </div>
        )}

        {activeTab === 'full' && (
          <div className="prose-sm max-w-none">
            {plan.plan_text ? (
              <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm">
                {renderMarkdown(plan.plan_text)}
              </div>
            ) : (
              <p className="text-gray-500 text-sm italic">No narrative plan generated.</p>
            )}
          </div>
        )}
      </div>

      <div className="bg-white/50 border-t border-green-200 px-5 py-3 text-xs text-gray-500 flex items-center justify-between">
        <span>Generated {plan.generated_at ? new Date(plan.generated_at).toLocaleString() : 'just now'}</span>
        <span className="italic">Always verify visa requirements with official sources</span>
      </div>
    </div>
  );
}
