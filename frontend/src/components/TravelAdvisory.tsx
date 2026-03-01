'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react';

interface AdvisoryData {
  score: number;
  sources_active: number;
  message: string;
  updated: string;
}

const LEVEL_CONFIG = {
  1: { label: 'Safe', Icon: CheckCircle, bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200', dot: 'bg-green-500' },
  2: { label: 'Low Risk', Icon: Info, bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', dot: 'bg-blue-500' },
  3: { label: 'Some Risk', Icon: AlertTriangle, bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', dot: 'bg-yellow-500' },
  4: { label: 'High Risk', Icon: AlertTriangle, bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', dot: 'bg-orange-500' },
  5: { label: 'Extreme', Icon: XCircle, bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', dot: 'bg-red-500' },
} as const;

// Map common country names to ISO 2-letter codes
const COUNTRY_CODES: Record<string, string> = {
  'Afghanistan': 'AF', 'Albania': 'AL', 'Algeria': 'DZ', 'Argentina': 'AR',
  'Armenia': 'AM', 'Australia': 'AU', 'Austria': 'AT', 'Azerbaijan': 'AZ',
  'Bahamas': 'BS', 'Bahrain': 'BH', 'Bangladesh': 'BD', 'Belgium': 'BE',
  'Belize': 'BZ', 'Bolivia': 'BO', 'Bosnia': 'BA', 'Brazil': 'BR',
  'Bulgaria': 'BG', 'Cambodia': 'KH', 'Canada': 'CA', 'Chile': 'CL',
  'China': 'CN', 'Colombia': 'CO', 'Costa Rica': 'CR', 'Croatia': 'HR',
  'Cuba': 'CU', 'Cyprus': 'CY', 'Czech Republic': 'CZ', 'Czechia': 'CZ',
  'Denmark': 'DK', 'Dominican Republic': 'DO', 'Ecuador': 'EC', 'Egypt': 'EG',
  'Estonia': 'EE', 'Ethiopia': 'ET', 'Finland': 'FI', 'France': 'FR',
  'Georgia': 'GE', 'Germany': 'DE', 'Ghana': 'GH', 'Greece': 'GR',
  'Guatemala': 'GT', 'Honduras': 'HN', 'Hungary': 'HU', 'Iceland': 'IS',
  'India': 'IN', 'Indonesia': 'ID', 'Iran': 'IR', 'Iraq': 'IQ',
  'Ireland': 'IE', 'Israel': 'IL', 'Italy': 'IT', 'Jamaica': 'JM',
  'Japan': 'JP', 'Jordan': 'JO', 'Kazakhstan': 'KZ', 'Kenya': 'KE',
  'Kosovo': 'XK', 'Kuwait': 'KW', 'Kyrgyzstan': 'KG', 'Laos': 'LA',
  'Latvia': 'LV', 'Lebanon': 'LB', 'Lithuania': 'LT', 'Luxembourg': 'LU',
  'Malaysia': 'MY', 'Maldives': 'MV', 'Malta': 'MT', 'Mexico': 'MX',
  'Moldova': 'MD', 'Mongolia': 'MN', 'Montenegro': 'ME', 'Morocco': 'MA',
  'Myanmar': 'MM', 'Namibia': 'NA', 'Nepal': 'NP', 'Netherlands': 'NL',
  'New Zealand': 'NZ', 'Nicaragua': 'NI', 'Nigeria': 'NG', 'North Macedonia': 'MK',
  'Norway': 'NO', 'Oman': 'OM', 'Pakistan': 'PK', 'Panama': 'PA',
  'Paraguay': 'PY', 'Peru': 'PE', 'Philippines': 'PH', 'Poland': 'PL',
  'Portugal': 'PT', 'Qatar': 'QA', 'Romania': 'RO', 'Russia': 'RU',
  'Saudi Arabia': 'SA', 'Senegal': 'SN', 'Serbia': 'RS', 'Singapore': 'SG',
  'Slovakia': 'SK', 'Slovenia': 'SI', 'South Africa': 'ZA', 'South Korea': 'KR',
  'Spain': 'ES', 'Sri Lanka': 'LK', 'Sweden': 'SE', 'Switzerland': 'CH',
  'Syria': 'SY', 'Taiwan': 'TW', 'Tajikistan': 'TJ', 'Tanzania': 'TZ',
  'Thailand': 'TH', 'Tunisia': 'TN', 'Turkey': 'TR', 'Türkiye': 'TR',
  'Turkmenistan': 'TM', 'Uganda': 'UG', 'Ukraine': 'UA',
  'United Arab Emirates': 'AE', 'UAE': 'AE', 'United Kingdom': 'GB', 'UK': 'GB',
  'United States': 'US', 'USA': 'US', 'Uruguay': 'UY', 'Uzbekistan': 'UZ',
  'Venezuela': 'VE', 'Vietnam': 'VN', 'Yemen': 'YE', 'Zambia': 'ZM',
  'Zimbabwe': 'ZW',
};

export function getCountryCode(countryName: string): string | null {
  if (!countryName) return null;
  // Direct match
  if (COUNTRY_CODES[countryName]) return COUNTRY_CODES[countryName];
  // Case-insensitive match
  const lower = countryName.toLowerCase();
  const entry = Object.entries(COUNTRY_CODES).find(([k]) => k.toLowerCase() === lower);
  return entry ? entry[1] : null;
}

// Shared in-memory cache (5 min TTL)
const CACHE: Record<string, { data: AdvisoryData; ts: number }> = {};

interface TravelAdvisoryProps {
  countryName: string;
  compact?: boolean;
}

export default function TravelAdvisory({ countryName, compact = false }: TravelAdvisoryProps) {
  const [advisory, setAdvisory] = useState<AdvisoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const countryCode = getCountryCode(countryName);

  useEffect(() => {
    if (!countryCode) { setLoading(false); return; }
    const cached = CACHE[countryCode];
    if (cached && Date.now() - cached.ts < 300_000) {
      setAdvisory(cached.data);
      setLoading(false);
      return;
    }
    setLoading(true);
    fetch(`https://www.travel-advisory.info/api?countrycode=${countryCode}`)
      .then((r) => r.json())
      .then((json) => {
        const data: AdvisoryData = json?.data?.[countryCode]?.advisory;
        if (data) {
          CACHE[countryCode] = { data, ts: Date.now() };
          setAdvisory(data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [countryCode]);

  if (!countryCode || (!loading && !advisory)) return null;

  if (loading) {
    return compact ? (
      <span className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-400 px-2 py-0.5 rounded-full animate-pulse">
        Advisory…
      </span>
    ) : (
      <div className="h-16 bg-gray-50 border border-gray-100 rounded-xl animate-pulse" />
    );
  }

  if (!advisory) return null;

  const level = Math.min(5, Math.max(1, Math.round(advisory.score))) as keyof typeof LEVEL_CONFIG;
  const config = LEVEL_CONFIG[level];
  const { Icon } = config;

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${config.bg} ${config.text} ${config.border}`}
        title={advisory.message}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
        {config.label}
      </span>
    );
  }

  return (
    <div className={`border rounded-xl p-4 ${config.bg} ${config.border}`}>
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${config.text}`} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h4 className={`font-semibold text-sm ${config.text}`}>
              Travel Advisory — {countryName}
            </h4>
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded-full bg-white/60 ${config.text}`}
            >
              {config.label} · {advisory.score.toFixed(1)}/5
            </span>
          </div>
          <p className={`text-sm ${config.text} opacity-90`}>{advisory.message}</p>
          <p className="text-xs text-gray-400 mt-1">
            Updated {advisory.updated} · {advisory.sources_active} source
            {advisory.sources_active !== 1 ? 's' : ''}
          </p>
        </div>
      </div>
    </div>
  );
}
