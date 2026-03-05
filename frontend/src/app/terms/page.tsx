export const metadata = {
  title: 'Terms of Service - TravelAI',
  description: 'Terms for using TravelAI recommendations and planning tools.',
};

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm p-8">
        <h1 className="text-3xl font-bold mb-4">Terms of Service</h1>
        <p className="text-gray-600 mb-6">Last updated: March 5, 2026</p>

        <section className="space-y-4 text-sm text-gray-700">
          <p>
            TravelAI provides planning assistance and recommendations. It does not guarantee
            availability, pricing, immigration eligibility, or legal compliance.
          </p>
          <p>
            You are responsible for confirming visas, entry rules, health requirements, and
            booking conditions with official providers before travel.
          </p>
          <p>
            Use of the service is subject to fair-use limits and abuse protection controls.
          </p>
          <p>
            By using TravelAI, you agree to these terms and applicable privacy practices.
          </p>
        </section>
      </div>
    </main>
  );
}

