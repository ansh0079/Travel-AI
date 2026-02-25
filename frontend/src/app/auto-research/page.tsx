import AutoResearchForm from '@/components/AutoResearchForm';

export const metadata = {
  title: 'AI Auto Research - TravelAI',
  description: 'Let our AI agent automatically research destinations for you based on your preferences',
};

export default function AutoResearchPage() {
  return (
    <main className="min-h-screen bg-gray-50 py-12">
      <AutoResearchForm />
    </main>
  );
}
