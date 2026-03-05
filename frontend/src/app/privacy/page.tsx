export const metadata = {
  title: 'Privacy Policy - TravelAI',
  description: 'How TravelAI handles your data and retention windows.',
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm p-8">
        <h1 className="text-3xl font-bold mb-4">Privacy Policy</h1>
        <p className="text-gray-600 mb-6">Last updated: March 5, 2026</p>

        <section className="space-y-4 text-sm text-gray-700">
          <p>
            TravelAI stores travel preferences, chat context, and analytics events to improve
            recommendations and product quality.
          </p>
          <p>
            Chat sessions are retained for a limited period defined by backend settings
            (`CHAT_RETENTION_DAYS`). Product analytics events are retained according to
            `ANALYTICS_RETENTION_DAYS`.
          </p>
          <p>
            We recommend verifying visa rules, legal requirements, and live pricing through
            official sources before booking.
          </p>
          <p>
            For account and data requests, contact support through the app contact channel.
          </p>
        </section>
      </div>
    </main>
  );
}

