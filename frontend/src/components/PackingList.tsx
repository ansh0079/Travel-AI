'use client';

import { useState, useEffect } from 'react';
import { Check, RotateCcw } from 'lucide-react';

interface PackingCategory {
  name: string;
  icon: string;
  items: string[];
}

const BASE_CATEGORIES: PackingCategory[] = [
  {
    name: 'Documents',
    icon: '📄',
    items: [
      'Passport (valid 6+ months)',
      'Travel insurance docs',
      'Visa / entry documents',
      'Booking confirmations',
      'Emergency contacts list',
      'Copies of ID (digital + printed)',
    ],
  },
  {
    name: 'Electronics',
    icon: '🔌',
    items: [
      'Phone + charger',
      'Power bank (20 000 mAh)',
      'Universal power adapter',
      'Earphones / headphones',
      'Camera + memory card',
    ],
  },
  {
    name: 'Health',
    icon: '💊',
    items: [
      'Prescription medications',
      'First-aid kit',
      'Hand sanitiser',
      'Pain relief (ibuprofen / paracetamol)',
      'Antihistamines',
      'Sunscreen SPF 50+',
    ],
  },
  {
    name: 'Money',
    icon: '💳',
    items: [
      'Credit / debit cards',
      'Local cash (small notes)',
      'Travel money card',
      'Emergency reserve (hidden)',
    ],
  },
  {
    name: 'Clothing',
    icon: '👕',
    items: [
      'T-shirts / tops (×5)',
      'Trousers / shorts (×3)',
      'Underwear (×7)',
      'Socks (×5 pairs)',
      'Pyjamas / loungewear',
      'Light jacket / cardigan',
      'Comfortable walking shoes',
      'Sandals / flip flops',
    ],
  },
  {
    name: 'Toiletries',
    icon: '🧴',
    items: [
      'Toothbrush + toothpaste',
      'Shampoo + conditioner',
      'Deodorant',
      'Razor',
      'Moisturiser',
      'Lip balm',
    ],
  },
];

const TRIP_EXTRAS: Record<string, PackingCategory> = {
  beach: {
    name: 'Beach Extras',
    icon: '🏖️',
    items: [
      'Swimsuit / trunks (×2)',
      'Beach towel',
      'Reef-safe sunscreen',
      'Snorkelling gear',
      'Waterproof dry bag',
      'Rash guard',
      'Beach cover-up',
    ],
  },
  adventure: {
    name: 'Adventure Gear',
    icon: '🧗',
    items: [
      'Hiking boots (broken in)',
      'Trekking poles',
      'Rain jacket / poncho',
      'Quick-dry clothing',
      'Head torch + batteries',
      'Multi-tool / knife',
      'Water purification tablets',
      'Blister plasters',
    ],
  },
  winter: {
    name: 'Cold Weather',
    icon: '❄️',
    items: [
      'Thermal base layers',
      'Heavy winter coat',
      'Waterproof boots',
      'Insulated gloves',
      'Warm hat / beanie',
      'Scarf / balaclava',
      'Hand warmers',
    ],
  },
  family: {
    name: 'Kids & Family',
    icon: '👨‍👩‍👧',
    items: [
      'Kids snacks',
      'Tablet / entertainment device',
      'Baby wipes (×2 packs)',
      'Kids sunscreen SPF 50+',
      'Stroller / baby carrier',
      'Favourite toy / comfort item',
      'Kids first-aid essentials',
    ],
  },
  cultural: {
    name: 'Cultural Sightseeing',
    icon: '🏛️',
    items: [
      'Modest / temple-appropriate clothing',
      'Scarf (to cover shoulders)',
      'Flat comfortable shoes',
      'City guidebook / offline map',
      'Small day backpack',
      'Reusable water bottle',
    ],
  },
  luxury: {
    name: 'Luxury / Formal',
    icon: '✨',
    items: [
      'Formal outfit (×2)',
      'Dress shoes',
      'Evening bag / clutch',
      'Jewellery / accessories',
      'Dry-cleaning bags',
      'Fragrance / cologne',
    ],
  },
};

function buildCategories(tripType: string, hasKids: boolean, weather: string): PackingCategory[] {
  const cats = [...BASE_CATEGORIES];
  const type = tripType.toLowerCase();

  if (TRIP_EXTRAS[type]) cats.push(TRIP_EXTRAS[type]);
  if (hasKids && type !== 'family') cats.push(TRIP_EXTRAS.family);
  if ((weather === 'cold' || weather === 'snow') && type !== 'winter') cats.push(TRIP_EXTRAS.winter);

  return cats;
}

interface PackingListProps {
  tripType?: string;
  hasKids?: boolean;
  weather?: string;
  cityName?: string;
}

export default function PackingList({
  tripType = 'city',
  hasKids = false,
  weather = 'warm',
  cityName = 'trip',
}: PackingListProps) {
  const storageKey = `packing_${cityName.toLowerCase().replace(/\s+/g, '_')}_${tripType}`;
  const [categories] = useState<PackingCategory[]>(() =>
    buildCategories(tripType, hasKids, weather)
  );
  const [checked, setChecked] = useState<Set<string>>(() => {
    if (typeof window === 'undefined') return new Set();
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? new Set(JSON.parse(saved) as string[]) : new Set();
    } catch {
      return new Set();
    }
  });
  const [activeCategory, setActiveCategory] = useState(categories[0]?.name ?? '');

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify([...checked]));
  }, [checked, storageKey]);

  const toggle = (item: string) =>
    setChecked((prev) => {
      const next = new Set(prev);
      next.has(item) ? next.delete(item) : next.add(item);
      return next;
    });

  const totalItems = categories.reduce((acc, c) => acc + c.items.length, 0);
  const packedCount = checked.size;
  const progress = totalItems > 0 ? Math.round((packedCount / totalItems) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Progress */}
      <div className="p-4 bg-indigo-50 border border-indigo-100 rounded-xl">
        <div className="flex justify-between items-center mb-2">
          <span className="font-semibold text-indigo-900">Packing Progress</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-indigo-700">
              {packedCount} / {totalItems} packed
            </span>
            <button
              onClick={() => setChecked(new Set())}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title="Reset all"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        <div className="h-2.5 bg-indigo-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-600 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        {progress === 100 && (
          <p className="text-sm text-indigo-700 font-medium mt-2">
            ✅ All packed! Have a wonderful trip!
          </p>
        )}
      </div>

      {/* Category tabs */}
      <div className="flex gap-2 flex-wrap">
        {categories.map((cat) => {
          const catChecked = cat.items.filter((i) => checked.has(i)).length;
          const isActive = activeCategory === cat.name;
          return (
            <button
              key={cat.name}
              onClick={() => setActiveCategory(cat.name)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {cat.icon} {cat.name}
              {catChecked > 0 && (
                <span
                  className={`text-xs ${isActive ? 'text-indigo-200' : 'text-indigo-600'}`}
                >
                  ({catChecked}/{cat.items.length})
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Item list for active category */}
      {categories
        .filter((c) => c.name === activeCategory)
        .map((cat) => (
          <div key={cat.name} className="space-y-2">
            {cat.items.map((item) => {
              const isChecked = checked.has(item);
              return (
                <label
                  key={item}
                  className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors select-none ${
                    isChecked
                      ? 'bg-green-50 border border-green-200'
                      : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
                  }`}
                  onClick={() => toggle(item)}
                >
                  <div
                    className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                      isChecked ? 'bg-green-500 border-green-500' : 'border-gray-300'
                    }`}
                  >
                    {isChecked && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <span
                    className={`text-sm ${
                      isChecked ? 'line-through text-gray-400' : 'text-gray-700'
                    }`}
                  >
                    {item}
                  </span>
                </label>
              );
            })}
          </div>
        ))}
    </div>
  );
}
