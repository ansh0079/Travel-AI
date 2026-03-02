import type { ResearchResults } from '@/services/api';

type RankedDestination = {
  destination: string;
  score: number;
  reasons?: string[];
};

export function buildAutonomousSuggestionPrompt(
  suggestion: string,
  rankedDestinations: RankedDestination[],
  researchResults: ResearchResults | null
): string | null {
  const normalized = suggestion.trim().toLowerCase();
  const ranked = rankedDestinations.map((d) => d.destination).filter(Boolean);
  const recommended = (researchResults?.recommendations || [])
    .map((r) => (r as any)?.destination)
    .filter(Boolean) as string[];
  const pool = Array.from(new Set([...ranked, ...recommended]));

  if (normalized.includes('compare top destinations')) {
    if (pool.length >= 2) {
      return `Compare ${pool[0]} and ${pool[1]} for weather, budget, visa, and activities.`;
    }
    return 'Compare my top destination options for weather, budget, visa, and activities.';
  }

  if (normalized.includes('build itinerary')) {
    const top = pool[0];
    if (top) {
      return `Build a detailed 5-day itinerary for ${top} based on my preferences.`;
    }
    return 'Build a detailed 5-day itinerary based on my preferences.';
  }

  if (normalized.includes('show budget breakdown')) {
    if (pool.length > 0) {
      return `Show a budget breakdown for ${pool.slice(0, 3).join(', ')}, including flights, hotel, food, and activities.`;
    }
    return 'Show a detailed budget breakdown for my best destination options.';
  }

  return null;
}

export function getAutonomousSuggestionAction(
  suggestion: string
): 'compare' | 'itinerary' | 'budget' | null {
  const normalized = suggestion.trim().toLowerCase();
  if (normalized.includes('compare top destinations')) return 'compare';
  if (normalized.includes('build itinerary')) return 'itinerary';
  if (normalized.includes('show budget breakdown')) return 'budget';
  return null;
}
