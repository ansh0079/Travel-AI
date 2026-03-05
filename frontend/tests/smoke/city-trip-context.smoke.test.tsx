import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CityDetailsClient from '@/app/city/[name]/CityDetailsClient';
import { api } from '@/services/api';

const pushMock = jest.fn();

jest.mock('next/navigation', () => ({
  useParams: () => ({ name: 'paris' }),
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () =>
    new URLSearchParams(
      'origin=London&travel_start=2026-06-01&travel_end=2026-06-10&budget_level=moderate&passport_country=US'
    ),
}));

jest.mock('@/components/CurrencyConverter', () => () => <div data-testid="currency-converter" />);
jest.mock('@/components/PackingList', () => () => <div data-testid="packing-list" />);
jest.mock('@/components/TravelAdvisory', () => () => <div data-testid="travel-advisory" />);
jest.mock('@/components/ExpenseTracker', () => () => <div data-testid="expense-tracker" />);
jest.mock('@/components/TripAdvisorPanel', () => () => <div data-testid="tripadvisor-panel" />);
jest.mock('@/components/RedditInsights', () => () => <div data-testid="reddit-insights" />);
jest.mock('@/components/AttractionDetailModal', () => () => <div data-testid="attraction-modal" />);

jest.mock('@/services/api', () => ({
  api: {
    getCityDetails: jest.fn(),
  },
}));

describe('CityDetails trip context smoke', () => {
  beforeEach(() => {
    pushMock.mockReset();
    (api.getCityDetails as jest.Mock).mockResolvedValue({
      overview: {
        name: 'Paris',
        country: 'France',
        description: 'A city test fixture',
        best_time_to_visit: 'Spring',
        language: 'French',
        currency: 'EUR',
        time_zone: 'CET',
        emergency_number: '112',
      },
      weather: {
        current_temp: 22,
        condition: 'Sunny',
        humidity: 40,
        forecast: [{ day: 'Mon', temp: 23, condition: 'Sunny' }],
        best_time_to_visit: 'Spring',
        climate_overview: 'Mild',
      },
      flights: {
        from_origin: 'London',
        cheapest_price: 120,
        duration_hours: 1.5,
        airlines: ['TestAir'],
        flight_options: [],
      },
      attractions: { top_attractions: [], categories: [], total_count: 0 },
      events: { upcoming_events: [], festivals: [], total_count: 0 },
      hotels: {
        luxury_options: [],
        top_rated: [],
        budget_options: [],
        price_range: { min: 80, max: 400 },
      },
      restaurants: {
        top_restaurants: [],
        must_try_dishes: [],
        food_scene: 'Great',
        price_range: '$$',
      },
      transport: {
        from_airport: { recommended: 'Train', cost_range: '$10-$20', options: ['Train'] },
        public_transport: { available: true, types: ['Metro'], cost_per_ride: '$2', day_pass: '$8' },
        taxi_rideshare: { available: true, base_fare: '$5', apps: ['Uber'] },
        recommended_pass: 'Metro pass',
      },
      costs: {
        budget_daily: 80,
        moderate_daily: 150,
        luxury_daily: 350,
        meal_average: 20,
        transport_average: 10,
      },
      visa: {
        visa_required: false,
        visa_type: null,
        duration: null,
        cost: null,
        processing_time: null,
      },
      tips: ['Tip 1'],
      weather_alerts: [],
      images: { hero: 'https://example.com/hero.jpg', gallery: [], attractions: {} },
    });
  });

  it('updates query params when refreshing trip context', async () => {
    const user = userEvent.setup();
    render(<CityDetailsClient />);

    await screen.findByText(/trip context/i);

    const originInput = screen.getByLabelText(/where are you starting from\?/i);
    await user.clear(originInput);
    await user.type(originInput, 'Boston');

    const passportSelect = screen.getByLabelText(/passport/i);
    await user.selectOptions(passportSelect, 'CA');

    await user.click(screen.getByRole('button', { name: /refresh details/i }));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalled();
    });

    const pushedPath = String(pushMock.mock.calls[0][0]);
    expect(pushedPath).toContain('/city/paris?');
    expect(pushedPath).toContain('origin=Boston');
    expect(pushedPath).toContain('passport_country=CA');
  });
});

