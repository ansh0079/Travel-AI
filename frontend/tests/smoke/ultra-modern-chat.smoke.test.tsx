import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UltraModernChat from '@/components/UltraModernChat';

jest.mock('@/hooks/useChatPipeline', () => ({
  PIPELINE_STEPS: ['discover', 'shortlist', 'compare', 'itinerary', 'booking_checklist'],
  STAGE_LABELS: {
    discover: 'Discover',
    shortlist: 'Shortlist',
    compare: 'Compare',
    itinerary: 'Itinerary',
    booking_checklist: 'Booking Checklist',
  },
  useChatPipeline: () => ({
    planningStage: 'discover',
    setPlanningStage: jest.fn(),
    rankedDestinations: [],
    isRanking: false,
    isReady: false,
    setIsReady: jest.fn(),
    researchJob: null,
    researchResults: null,
    isResearching: false,
    syncMessageResult: jest.fn(),
    submitFeedback: jest.fn(),
    advanceStage: jest.fn(),
    clearSession: jest.fn(),
    trackRecommendationAccepted: jest.fn(),
  }),
}));

jest.mock('@/utils/autonomousSuggestionActions', () => ({
  buildAutonomousSuggestionPrompt: (prompt: string) => prompt,
  getAutonomousSuggestionAction: () => null,
}));

jest.mock('@/components/DestinationMiniCard', () => () => <div data-testid="destination-mini-card" />);

describe('UltraModernChat smoke', () => {
  it('accepts user typing in chat input', async () => {
    const user = userEvent.setup();
    render(<UltraModernChat onComplete={jest.fn()} />);

    const input = screen.getByPlaceholderText(/describe your dream trip/i);
    await user.type(input, 'I want to go to Rome in July from Boston');

    expect(input).toHaveValue('I want to go to Rome in July from Boston');
  });
});

