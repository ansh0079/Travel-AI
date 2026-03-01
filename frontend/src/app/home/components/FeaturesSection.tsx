'use client';

import { motion } from 'framer-motion';

const features = [
  {
    step: '1',
    icon: '💬',
    title: 'Tell Us Your Preferences',
    description:
      'Answer a few quick questions about your ideal trip - duration, budget, interests, and more.',
  },
  {
    step: '2',
    icon: '🤖',
    title: 'AI Analysis',
    description:
      'Our AI analyzes weather, affordability, visa requirements, attractions, and events in real-time.',
  },
  {
    step: '3',
    icon: '✈️',
    title: 'Get Recommendations',
    description:
      'Receive personalized destination recommendations with detailed insights for each location.',
  },
];

export default function FeaturesSection() {
  return (
    <section className="max-w-6xl mx-auto px-4 py-24">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="text-center mb-16"
      >
        <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">How It Works</h2>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Our AI analyzes thousands of destinations to find your perfect match
        </p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {features.map((feature, i) => (
          <motion.div
            key={i}
            className="bg-white rounded-2xl shadow-lg p-8 text-center relative"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            viewport={{ once: true }}
          >
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold text-sm">
              {feature.step}
            </div>
            <div className="text-5xl mb-4">{feature.icon}</div>
            <h3 className="text-xl font-bold mb-3 text-gray-900">{feature.title}</h3>
            <p className="text-gray-600 leading-relaxed">{feature.description}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
