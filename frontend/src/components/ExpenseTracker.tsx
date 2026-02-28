'use client';

import { useState, useEffect } from 'react';
import { Plus, Trash2, DollarSign } from 'lucide-react';

interface Expense {
  id: string;
  category: string;
  description: string;
  amount: number;
  date: string;
}

const CATEGORIES = [
  { id: 'accommodation', label: 'Accommodation', icon: '🏨' },
  { id: 'food', label: 'Food & Drinks', icon: '🍽️' },
  { id: 'transport', label: 'Transport', icon: '🚇' },
  { id: 'activities', label: 'Activities', icon: '🎭' },
  { id: 'shopping', label: 'Shopping', icon: '🛍️' },
  { id: 'other', label: 'Other', icon: '📦' },
];

interface ExpenseTrackerProps {
  cityName: string;
  dailyBudgetUSD?: number;
  travelDays?: number;
}

export default function ExpenseTracker({
  cityName,
  dailyBudgetUSD = 150,
  travelDays = 7,
}: ExpenseTrackerProps) {
  const storageKey = `expenses_${cityName.toLowerCase().replace(/\s+/g, '_')}`;
  const totalBudget = dailyBudgetUSD * travelDays;

  const [expenses, setExpenses] = useState<Expense[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      return JSON.parse(localStorage.getItem(storageKey) || '[]') as Expense[];
    } catch {
      return [];
    }
  });

  const [form, setForm] = useState({ category: 'food', description: '', amount: '' });
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(expenses));
  }, [expenses, storageKey]);

  const totalSpent = expenses.reduce((s, e) => s + e.amount, 0);
  const remaining = totalBudget - totalSpent;
  const pct = Math.min(100, Math.round((totalSpent / totalBudget) * 100));

  const addExpense = () => {
    const amt = parseFloat(form.amount);
    if (!form.description.trim() || isNaN(amt) || amt <= 0) return;
    setExpenses((prev) => [
      {
        id: Date.now().toString(),
        category: form.category,
        description: form.description.trim(),
        amount: amt,
        date: new Date().toLocaleDateString(),
      },
      ...prev,
    ]);
    setForm({ category: 'food', description: '', amount: '' });
    setShowForm(false);
  };

  const byCategory = CATEGORIES.map((cat) => ({
    ...cat,
    total: expenses.filter((e) => e.category === cat.id).reduce((s, e) => s + e.amount, 0),
  })).filter((c) => c.total > 0);

  return (
    <div className="space-y-4">
      {/* Budget overview */}
      <div className="bg-white border rounded-xl p-4">
        <h4 className="font-semibold text-gray-900 mb-3">Budget Tracker — {cityName}</h4>

        <div className="grid grid-cols-3 gap-3 mb-4 text-center">
          <div className="bg-blue-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-0.5">Total Budget</p>
            <p className="text-lg font-bold text-blue-700">${totalBudget.toFixed(0)}</p>
            <p className="text-xs text-gray-400">${dailyBudgetUSD}/d × {travelDays}d</p>
          </div>
          <div className="bg-orange-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-0.5">Spent</p>
            <p className="text-lg font-bold text-orange-700">${totalSpent.toFixed(2)}</p>
          </div>
          <div className={`rounded-lg p-3 ${remaining >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
            <p className="text-xs text-gray-500 mb-0.5">Remaining</p>
            <p className={`text-lg font-bold ${remaining >= 0 ? 'text-green-700' : 'text-red-700'}`}>
              {remaining < 0 && '-'}${Math.abs(remaining).toFixed(2)}
            </p>
            {remaining < 0 && <p className="text-xs text-red-500">over budget</p>}
          </div>
        </div>

        {/* Progress bar */}
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Budget used</span>
          <span>{pct}%</span>
        </div>
        <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden mb-3">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              pct > 100 ? 'bg-red-500' : pct > 80 ? 'bg-orange-500' : 'bg-green-500'
            }`}
            style={{ width: `${Math.min(100, pct)}%` }}
          />
        </div>

        {/* Category breakdown */}
        {byCategory.length > 0 && (
          <div className="space-y-1 pt-2 border-t">
            {byCategory.map((cat) => (
              <div key={cat.id} className="flex items-center gap-2 text-sm">
                <span>{cat.icon}</span>
                <span className="flex-1 text-gray-600">{cat.label}</span>
                <span className="font-medium text-gray-800">${cat.total.toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add expense form */}
      {showForm ? (
        <div className="bg-gray-50 border rounded-xl p-4 space-y-3">
          <p className="font-medium text-gray-700 text-sm">Add Expense</p>
          {/* Category selector */}
          <div className="grid grid-cols-3 gap-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setForm((f) => ({ ...f, category: cat.id }))}
                className={`flex items-center gap-1.5 p-2 rounded-lg text-xs transition-colors ${
                  form.category === cat.id
                    ? 'bg-indigo-100 text-indigo-700 border border-indigo-300'
                    : 'bg-white hover:bg-gray-100 border border-gray-200'
                }`}
              >
                <span>{cat.icon}</span> {cat.label}
              </button>
            ))}
          </div>

          <input
            type="text"
            placeholder="Description (e.g. Lunch at market)"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />

          <div className="flex gap-2">
            <div className="relative flex-1">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="Amount (USD)"
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                onKeyDown={(e) => e.key === 'Enter' && addExpense()}
                className="w-full border rounded-lg pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <button
              onClick={addExpense}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 transition-colors"
            >
              Add
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="w-full flex items-center justify-center gap-2 py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-indigo-400 hover:text-indigo-600 transition-colors text-sm"
        >
          <Plus className="w-4 h-4" /> Add Expense
        </button>
      )}

      {/* Expense list */}
      {expenses.length > 0 && (
        <div className="space-y-2">
          <p className="font-medium text-gray-700 text-sm">Recent Expenses</p>
          {expenses.map((expense) => {
            const cat = CATEGORIES.find((c) => c.id === expense.category);
            return (
              <div
                key={expense.id}
                className="flex items-center gap-3 p-3 bg-white border rounded-lg"
              >
                <span className="text-xl flex-shrink-0">{cat?.icon || '📦'}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {expense.description}
                  </p>
                  <p className="text-xs text-gray-400">
                    {cat?.label} · {expense.date}
                  </p>
                </div>
                <span className="font-semibold text-gray-800">${expense.amount.toFixed(2)}</span>
                <button
                  onClick={() =>
                    setExpenses((prev) => prev.filter((e) => e.id !== expense.id))
                  }
                  className="text-gray-300 hover:text-red-400 transition-colors flex-shrink-0"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {expenses.length === 0 && !showForm && (
        <p className="text-center text-sm text-gray-400 py-4">
          No expenses logged yet — add your first!
        </p>
      )}
    </div>
  );
}
