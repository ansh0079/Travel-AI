import { fireEvent, render, screen } from '@testing-library/react';
import { AutonomousResearchForm } from '@/components/AutonomousResearchForm';

jest.mock('@/hooks/useResearch', () => ({
  useResearch: () => ({
    startResearch: jest.fn(),
    cancelResearch: jest.fn(),
    status: 'idle',
    progress: 0,
    currentStep: '',
    results: null,
    error: null,
    messages: [],
    isConnected: false,
    jobId: null,
  }),
}));

describe('AutonomousResearchForm smoke', () => {
  it('allows typing in the start location field', async () => {
    render(<AutonomousResearchForm />);

    const originInput = screen.getByPlaceholderText(/e\.g\., new york/i);
    fireEvent.change(originInput, { target: { value: 'New York' } });

    expect(originInput).toHaveValue('New York');
  });
});
