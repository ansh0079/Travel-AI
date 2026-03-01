export default function FooterSection() {
  const footerLinks = [
    {
      title: 'Features',
      links: ['AI Recommendations', 'Weather Forecasts', 'Visa Information', 'Cost Analysis'],
    },
    {
      title: 'Destinations',
      links: ['Europe', 'Asia', 'Americas', 'Africa & Middle East'],
    },
    {
      title: 'Connect',
      links: ['About Us', 'Contact', 'Privacy Policy', 'Terms of Service'],
    },
  ];

  return (
    <footer className="bg-gray-900 text-white py-16">
      <div className="max-w-6xl mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-2xl font-bold mb-4">TravelAI</h3>
            <p className="text-gray-400">
              Your AI-powered travel companion for discovering the perfect destinations.
            </p>
          </div>
          {footerLinks.map((section) => (
            <div key={section.title}>
              <h4 className="font-semibold mb-4">{section.title}</h4>
              <ul className="space-y-2 text-gray-400">
                {section.links.map((link) => (
                  <li key={link}>
                    <a href="#" className="hover:text-white transition-colors">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t border-gray-800 mt-12 pt-8 text-center text-gray-500">
          © {new Date().getFullYear()} TravelAI. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
