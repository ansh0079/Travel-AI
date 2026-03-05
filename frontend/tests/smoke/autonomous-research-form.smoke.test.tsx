import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
    const user = userEvent.setup();
    render(<AutonomousResearchForm />);

    const originInput = screen.getByLabelText(/where are you starting from\?/i);
    await user.type(originInput, 'New York');

    expect(originInput).toHaveValue('New York');
  });
});

