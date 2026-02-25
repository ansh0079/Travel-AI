import { AutonomousResearchForm } from "@/components/AutonomousResearchForm";

export const metadata = {
  title: "AI Travel Research - TravelAI",
  description: "Let our AI agent research destinations for you in real-time",
};

export default function ResearchPage() {
  return (
    <main className="min-h-screen bg-gray-50 py-8">
      <AutonomousResearchForm />
    </main>
  );
}
