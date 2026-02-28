'use client';

import { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';

interface CurrencyConverterProps {
  amountUSD: number;
  label?: string;
  targetCurrency?: string;
}

const POPULAR_CURRENCIES = [
  'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'SGD', 'AED',
  'INR', 'THB', 'CHF', 'BRL', 'MXN', 'ZAR', 'TRY', 'IDR', 'PHP',
];

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', AUD: 'A$', CAD: 'C$',
  CHF: 'Fr', CNY: '¥', INR: '₹', BRL: 'R$', MXN: '$', SGD: 'S$',
  HKD: 'HK$', NOK: 'kr', SEK: 'kr', DKK: 'kr', NZD: 'NZ$', ZAR: 'R',
  THB: '฿', IDR: 'Rp', MYR: 'RM', PHP: '₱', TRY: '₺', AED: 'د.إ',
  SAR: '﷼', EGP: '£', MAD: 'MAD',
};

// Static fallback rates (updated periodically, good enough for estimates)
const FALLBACK_RATES: Record<string, number> = {
  USD: 1, EUR: 0.92, GBP: 0.79, JPY: 149.5, AUD: 1.53, CAD: 1.36,
  CHF: 0.89, CNY: 7.24, INR: 83.12, BRL: 4.97, MXN: 17.15, SGD: 1.34,
  HKD: 7.82, THB: 35.1, AED: 3.67, TRY: 32.5, ZAR: 18.63, IDR: 15600,
  PHP: 56.4, MAD: 10.0, EGP: 30.9,
};

// Module-level cache so all instances share rates
let _cachedRates: Record<string, number> | null = null;
let _cacheDate: string | null = null;

export default function CurrencyConverter({
  amountUSD,
  label = 'Daily Cost',
  targetCurrency = 'EUR',
}: CurrencyConverterProps) {
  const [rates, setRates] = useState<Record<string, number> | null>(_cachedRates);
  const [currency, setCurrency] = useState(targetCurrency);
  const [loading, setLoading] = useState(!_cachedRates);
  const [rateDate, setRateDate] = useState<string | null>(_cacheDate);

  useEffect(() => {
    if (_cachedRates) return;
    setLoading(true);
    fetch('https://api.exchangerate-api.com/v4/latest/USD')
      .then((r) => r.json())
      .then((d) => {
        _cachedRates = d.rates;
        _cacheDate = d.date;
        setRates(d.rates);
        setRateDate(d.date);
      })
      .catch(() => {
        _cachedRates = FALLBACK_RATES;
        setRates(FALLBACK_RATES);
      })
      .finally(() => setLoading(false));
  }, []);

  const rate = rates?.[currency] ?? FALLBACK_RATES[currency] ?? 1;
  const converted = (amountUSD * rate).toFixed(
    currency === 'JPY' || currency === 'IDR' || currency === 'KRW' ? 0 : 2
  );
  const symbol = CURRENCY_SYMBOLS[currency] || currency + ' ';

  return (
    <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-emerald-900 text-sm">💱 {label} Converter</h4>
        {rateDate && (
          <span className="text-xs text-gray-400">Rates: {rateDate}</span>
        )}
      </div>

      <div className="flex items-center gap-3 mb-3">
        <div className="flex-1 text-center p-3 bg-white rounded-lg shadow-sm border border-emerald-100">
          <p className="text-xs text-gray-500 mb-1">USD</p>
          <p className="text-2xl font-bold text-gray-900">${amountUSD}</p>
        </div>
        <span className="text-gray-400 text-xl font-light">=</span>
        <div className="flex-1 text-center p-3 bg-emerald-600 rounded-lg shadow-sm">
          <p className="text-xs text-emerald-200 mb-1">{currency}</p>
          {loading ? (
            <RefreshCw className="w-5 h-5 animate-spin mx-auto text-white" />
          ) : (
            <p className="text-2xl font-bold text-white">
              {symbol}{converted}
            </p>
          )}
        </div>
      </div>

      <select
        value={currency}
        onChange={(e) => setCurrency(e.target.value)}
        className="w-full text-sm border border-emerald-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-400"
      >
        {POPULAR_CURRENCIES.map((c) => (
          <option key={c} value={c}>
            {c} {CURRENCY_SYMBOLS[c] ? `— ${CURRENCY_SYMBOLS[c]}` : ''}
          </option>
        ))}
      </select>
    </div>
  );
}
