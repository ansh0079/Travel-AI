'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MapPin, ExternalLink, Camera, Zap, Link2, ChevronLeft, ChevronRight } from 'lucide-react';

// ── Curated Unsplash photo IDs (no API key needed) ──────────────────────────
const CITY_PHOTO_IDS: Record<string, string> = {
  paris: '1502602898657-3e91760cbb34',
  london: '1513635269975-59663e0ac1ad',
  rome: '1552832230-c0197dd311b5',
  barcelona: '1539037116277-4db20889f2d4',
  amsterdam: '1534351590666-13e3e96b5017',
  lisbon: '1555881400-74d7acaacd8b',
  prague: '1541849546-216549ae216d',
  athens: '1555993539-1732b0258235',
  santorini: '1570077188670-e3a8d69ac5ff',
  budapest: '1570031880-24cfe5faf6f0',
  florence: '1541370976299-4d24ebbc9077',
  venice: '1523906834658-6e24ef2386f9',
  vienna: '1516550135131-7d7b0e93234d',
  istanbul: '1524231757912-21f4fe3a7200',
  tokyo: '1540959733332-eab4deabeeaf',
  kyoto: '1545569341-9eb8b30979d9',
  bali: '1537996194471-e657df975ab4',
  bangkok: '1508009603885-50cf7c579365',
  singapore: '1525625293386-3f8f99389edd',
  maldives: '1573843981267-be1999ff37cd',
  'hong kong': '1536599018102-9f803c140fc1',
  seoul: '1548534504-f07b6c7c3c7e',
  phuket: '1537953773345-d172ccf13cf1',
  dubai: '1512453979798-5ea266f8880c',
  'new york': '1496442226666-8d4d0e62e6e9',
  'new york city': '1496442226666-8d4d0e62e6e9',
  miami: '1507525428034-b723cf961d3e',
  cancun: '1507525428034-b723cf961d3e',
  'rio de janeiro': '1483729558449-99ef09a8c71f',
  'cape town': '1580060839134-75a5edca2e99',
  sydney: '1506973035872-a4ec16b8e8d9',
  marrakech: '1553787499-6f9133860278',
  cairo: '1539650116574-75c0c6d73f6e',
  reykjavik: '1506905925346-21bda4d32df4',
  'algarve': '1520208760088-fc069a4d3c5d',
  'costa brava': '1503917988-162729beb4ba',
  'costa dorada': '1503917988-162729beb4ba',
  portugal: '1555881400-74d7acaacd8b',
  spain: '1539037116277-4db20889f2d4',
  japan: '1540959733332-eab4deabeeaf',
  thailand: '1508009603885-50cf7c579365',
  indonesia: '1537996194471-e657df975ab4',
  greece: '1570077188670-e3a8d69ac5ff',
  'mexico city': '1518105779142-d975f22f1b0a',
  'buenos aires': '1541323302-2f4ad7df97c9',
  berlin: '1560969184-10fe8719e047',
  edinburgh: '1548777123-e216912df7d8',
  oslo: '1513622470522-26c3c8a854bc',
  stockholm: '1509356843151-3e7d96241e11',
  copenhagen: '1513553404607-988bf2703777',
  toronto: '1517935706615-2717063c2225',
  vancouver: '1560814304-4f05b62af116',
  amalfi: '1533587851344-c7b2d7f14d5b',
};

// ── Curated destination details ──────────────────────────────────────────────
interface DestinationInfo {
  country: string;
  flag: string;
  attractions: Array<{ name: string; emoji: string; type: string }>;
  activities: string[];
  bestFor: string[];
}

const DESTINATION_DATA: Record<string, DestinationInfo> = {
  paris: {
    country: 'France', flag: '🇫🇷',
    attractions: [
      { name: 'Eiffel Tower', emoji: '🗼', type: 'Landmark' },
      { name: 'Louvre Museum', emoji: '🏛️', type: 'Museum' },
      { name: 'Notre-Dame Cathedral', emoji: '⛪', type: 'Heritage' },
      { name: 'Champs-Élysées', emoji: '🛍️', type: 'Shopping' },
      { name: 'Musée d\'Orsay', emoji: '🎨', type: 'Museum' },
    ],
    activities: ['Seine river cruise', 'Wine & cheese tasting', 'Cooking class', 'Montmartre walk', 'Fashion district tour', 'Versailles day trip'],
    bestFor: ['Romance', 'Culture', 'Food', 'Art', 'Fashion'],
  },
  london: {
    country: 'United Kingdom', flag: '🇬🇧',
    attractions: [
      { name: 'Tower of London', emoji: '🏰', type: 'Heritage' },
      { name: 'British Museum', emoji: '🏛️', type: 'Museum' },
      { name: 'Buckingham Palace', emoji: '👑', type: 'Landmark' },
      { name: 'Tower Bridge', emoji: '🌉', type: 'Landmark' },
      { name: 'Westminster Abbey', emoji: '⛪', type: 'Heritage' },
    ],
    activities: ['Thames river cruise', 'West End show', 'Borough Market food tour', 'Hyde Park picnic', 'Pub crawl', 'Day trip to Stonehenge'],
    bestFor: ['History', 'Culture', 'Theatre', 'Shopping', 'Food'],
  },
  rome: {
    country: 'Italy', flag: '🇮🇹',
    attractions: [
      { name: 'Colosseum', emoji: '🏛️', type: 'Heritage' },
      { name: 'Vatican & Sistine Chapel', emoji: '⛪', type: 'Heritage' },
      { name: 'Trevi Fountain', emoji: '⛲', type: 'Landmark' },
      { name: 'Roman Forum', emoji: '🏺', type: 'Heritage' },
      { name: 'Pantheon', emoji: '🏛️', type: 'Heritage' },
    ],
    activities: ['Pasta-making class', 'Gelato tasting tour', 'Vespa tour', 'Wine tasting in Trastevere', 'Catacombs visit', 'Day trip to Pompeii'],
    bestFor: ['History', 'Food', 'Art', 'Romance', 'Architecture'],
  },
  barcelona: {
    country: 'Spain', flag: '🇪🇸',
    attractions: [
      { name: 'Sagrada Família', emoji: '⛪', type: 'Architecture' },
      { name: 'Park Güell', emoji: '🌿', type: 'Park' },
      { name: 'Gothic Quarter', emoji: '🏛️', type: 'Heritage' },
      { name: 'Camp Nou', emoji: '⚽', type: 'Sports' },
      { name: 'La Boqueria Market', emoji: '🥦', type: 'Market' },
    ],
    activities: ['Tapas tour', 'Flamenco show', 'Beach volleyball', 'Bike tour', 'Cava tasting', 'Day trip to Montserrat'],
    bestFor: ['Beaches', 'Architecture', 'Food', 'Nightlife', 'Sports'],
  },
  amsterdam: {
    country: 'Netherlands', flag: '🇳🇱',
    attractions: [
      { name: 'Anne Frank House', emoji: '🏠', type: 'Heritage' },
      { name: 'Rijksmuseum', emoji: '🎨', type: 'Museum' },
      { name: 'Van Gogh Museum', emoji: '🖼️', type: 'Museum' },
      { name: 'Canal Ring', emoji: '⛵', type: 'Landmark' },
      { name: 'Vondelpark', emoji: '🌿', type: 'Park' },
    ],
    activities: ['Canal boat tour', 'Cycling tour', 'Dutch cheese tasting', 'Flower market visit', 'Heineken Experience', 'Keukenhof day trip'],
    bestFor: ['Culture', 'Cycling', 'Art', 'History', 'Nightlife'],
  },
  tokyo: {
    country: 'Japan', flag: '🇯🇵',
    attractions: [
      { name: 'Senso-ji Temple', emoji: '⛩️', type: 'Heritage' },
      { name: 'Shibuya Crossing', emoji: '🚦', type: 'Landmark' },
      { name: 'Tokyo Skytree', emoji: '🗼', type: 'Landmark' },
      { name: 'Shinjuku Gyoen', emoji: '🌸', type: 'Park' },
      { name: 'Tsukiji Outer Market', emoji: '🍣', type: 'Market' },
    ],
    activities: ['Sushi-making class', 'Tea ceremony', 'Sumo wrestling show', 'Anime district (Akihabara) tour', 'Day trip to Mt. Fuji', 'Robot Restaurant'],
    bestFor: ['Culture', 'Food', 'Technology', 'Anime', 'Shopping'],
  },
  kyoto: {
    country: 'Japan', flag: '🇯🇵',
    attractions: [
      { name: 'Fushimi Inari Shrine', emoji: '⛩️', type: 'Heritage' },
      { name: 'Arashiyama Bamboo Grove', emoji: '🎋', type: 'Nature' },
      { name: 'Kinkaku-ji (Golden Pavilion)', emoji: '🏯', type: 'Heritage' },
      { name: 'Gion District', emoji: '🏮', type: 'Heritage' },
      { name: 'Nishiki Market', emoji: '🥢', type: 'Market' },
    ],
    activities: ['Tea ceremony', 'Geisha district walk', 'Zen meditation', 'Kimono rental & photoshoot', 'Tofu cooking class', 'Nara deer park day trip'],
    bestFor: ['Culture', 'History', 'Temples', 'Nature', 'Traditional Arts'],
  },
  bali: {
    country: 'Indonesia', flag: '🇮🇩',
    attractions: [
      { name: 'Uluwatu Temple', emoji: '⛩️', type: 'Heritage' },
      { name: 'Tegallalang Rice Terraces', emoji: '🌾', type: 'Nature' },
      { name: 'Sacred Monkey Forest', emoji: '🐒', type: 'Nature' },
      { name: 'Tanah Lot Temple', emoji: '🌅', type: 'Heritage' },
      { name: 'Seminyak Beach', emoji: '🏖️', type: 'Beach' },
    ],
    activities: ['Surf lessons', 'Yoga retreat', 'Cooking class', 'Waterfall hiking', 'Kecak fire dance', 'Snorkelling at Nusa Penida'],
    bestFor: ['Beaches', 'Wellness', 'Culture', 'Surfing', 'Budget'],
  },
  bangkok: {
    country: 'Thailand', flag: '🇹🇭',
    attractions: [
      { name: 'Grand Palace & Wat Phra Kaew', emoji: '👑', type: 'Heritage' },
      { name: 'Wat Pho (Reclining Buddha)', emoji: '🛕', type: 'Heritage' },
      { name: 'Chatuchak Weekend Market', emoji: '🛍️', type: 'Market' },
      { name: 'Wat Arun (Temple of Dawn)', emoji: '🌅', type: 'Heritage' },
      { name: 'Khao San Road', emoji: '🍻', type: 'Entertainment' },
    ],
    activities: ['Floating market tour', 'Thai cooking class', 'Muay Thai class', 'Tuk-tuk city tour', 'Street food walk', 'Day trip to Ayutthaya'],
    bestFor: ['Food', 'Culture', 'Budget', 'Nightlife', 'Shopping'],
  },
  dubai: {
    country: 'UAE', flag: '🇦🇪',
    attractions: [
      { name: 'Burj Khalifa', emoji: '🏙️', type: 'Landmark' },
      { name: 'Dubai Mall & Fountain', emoji: '💦', type: 'Shopping' },
      { name: 'Palm Jumeirah', emoji: '🌴', type: 'Landmark' },
      { name: 'Dubai Creek & Old Souk', emoji: '⛵', type: 'Heritage' },
      { name: 'Desert Safari', emoji: '🏜️', type: 'Nature' },
    ],
    activities: ['Desert safari & dune bashing', 'Hot air balloon ride', 'Skydiving', 'Indoor ski slope', 'Dhow cruise dinner', 'Gold & spice souk tour'],
    bestFor: ['Luxury', 'Shopping', 'Adventure', 'Architecture', 'Families'],
  },
  singapore: {
    country: 'Singapore', flag: '🇸🇬',
    attractions: [
      { name: 'Gardens by the Bay', emoji: '🌿', type: 'Nature' },
      { name: 'Marina Bay Sands', emoji: '🏙️', type: 'Landmark' },
      { name: 'Sentosa Island', emoji: '🏖️', type: 'Entertainment' },
      { name: 'Chinatown & Little India', emoji: '🏮', type: 'Heritage' },
      { name: 'Singapore Zoo', emoji: '🦁', type: 'Nature' },
    ],
    activities: ['Hawker centre food tour', 'Night safari', 'Universal Studios', 'Boat Quay bar hop', 'Heritage neighbourhood walk', 'Cable car ride'],
    bestFor: ['Food', 'Families', 'Shopping', 'Cleanliness', 'Culture'],
  },
  'new york': {
    country: 'USA', flag: '🇺🇸',
    attractions: [
      { name: 'Statue of Liberty', emoji: '🗽', type: 'Landmark' },
      { name: 'Central Park', emoji: '🌿', type: 'Park' },
      { name: 'Times Square', emoji: '🎪', type: 'Landmark' },
      { name: 'Metropolitan Museum of Art', emoji: '🎨', type: 'Museum' },
      { name: 'Brooklyn Bridge', emoji: '🌉', type: 'Landmark' },
    ],
    activities: ['Broadway show', 'NYC food tour', 'High Line walk', 'Bike in Central Park', 'Gallery hopping in Chelsea', 'Day trip to the Hamptons'],
    bestFor: ['Culture', 'Food', 'Theatre', 'Shopping', 'Architecture'],
  },
  'new york city': {
    country: 'USA', flag: '🇺🇸',
    attractions: [
      { name: 'Statue of Liberty', emoji: '🗽', type: 'Landmark' },
      { name: 'Central Park', emoji: '🌿', type: 'Park' },
      { name: 'Times Square', emoji: '🎪', type: 'Landmark' },
      { name: 'Metropolitan Museum of Art', emoji: '🎨', type: 'Museum' },
      { name: 'Brooklyn Bridge', emoji: '🌉', type: 'Landmark' },
    ],
    activities: ['Broadway show', 'NYC food tour', 'High Line walk', 'Bike in Central Park', 'Gallery hopping in Chelsea', 'Day trip to the Hamptons'],
    bestFor: ['Culture', 'Food', 'Theatre', 'Shopping', 'Architecture'],
  },
  'cape town': {
    country: 'South Africa', flag: '🇿🇦',
    attractions: [
      { name: 'Table Mountain', emoji: '⛰️', type: 'Nature' },
      { name: 'Robben Island', emoji: '🏝️', type: 'Heritage' },
      { name: 'Boulders Beach (Penguins)', emoji: '🐧', type: 'Nature' },
      { name: 'V&A Waterfront', emoji: '⛵', type: 'Shopping' },
      { name: 'Boulders Beach', emoji: '🏖️', type: 'Beach' },
    ],
    activities: ['Table Mountain hike / cable car', 'Cape Winelands wine tour', 'Whale watching', 'Cage shark diving', 'Cape Point peninsula drive', 'Kalk Bay market'],
    bestFor: ['Nature', 'Adventure', 'Wine', 'Beaches', 'Wildlife'],
  },
  sydney: {
    country: 'Australia', flag: '🇦🇺',
    attractions: [
      { name: 'Sydney Opera House', emoji: '🎭', type: 'Landmark' },
      { name: 'Harbour Bridge', emoji: '🌉', type: 'Landmark' },
      { name: 'Bondi Beach', emoji: '🏄', type: 'Beach' },
      { name: 'Taronga Zoo', emoji: '🦘', type: 'Nature' },
      { name: 'The Rocks', emoji: '🏘️', type: 'Heritage' },
    ],
    activities: ['Bridge climb', 'Bondi to Coogee coastal walk', 'Opera House tour', 'Blue Mountains day trip', 'Whale watching', 'Manly ferry & beach'],
    bestFor: ['Beaches', 'Outdoors', 'Food', 'Culture', 'Families'],
  },
  marrakech: {
    country: 'Morocco', flag: '🇲🇦',
    attractions: [
      { name: 'Jemaa el-Fna Square', emoji: '🎪', type: 'Heritage' },
      { name: 'Bahia Palace', emoji: '🏰', type: 'Heritage' },
      { name: 'Majorelle Garden', emoji: '🌿', type: 'Nature' },
      { name: 'Medina Souks', emoji: '🛍️', type: 'Market' },
      { name: 'Saadian Tombs', emoji: '🏛️', type: 'Heritage' },
    ],
    activities: ['Hammam & spa', 'Cooking class', 'Atlas Mountains day trip', 'Camel trekking in Agafay desert', 'Souk haggling tour', 'Hot air balloon at sunrise'],
    bestFor: ['Culture', 'Food', 'Markets', 'Budget', 'Adventure'],
  },
  reykjavik: {
    country: 'Iceland', flag: '🇮🇸',
    attractions: [
      { name: 'Hallgrímskirkja Church', emoji: '⛪', type: 'Landmark' },
      { name: 'Northern Lights', emoji: '🌌', type: 'Nature' },
      { name: 'Blue Lagoon', emoji: '♨️', type: 'Wellness' },
      { name: 'Þingvellir National Park', emoji: '🏔️', type: 'Nature' },
      { name: 'Harpa Concert Hall', emoji: '🎵', type: 'Culture' },
    ],
    activities: ['Northern Lights tour', 'Golden Circle tour', 'Glacier hiking', 'Whale watching', 'Snorkelling between tectonic plates', 'Midnight sun experience'],
    bestFor: ['Nature', 'Adventure', 'Unique Experiences', 'Photography', 'Outdoors'],
  },
  maldives: {
    country: 'Maldives', flag: '🇲🇻',
    attractions: [
      { name: 'Underwater Restaurant', emoji: '🐠', type: 'Dining' },
      { name: 'Male Coral Reefs', emoji: '🪸', type: 'Nature' },
      { name: 'Overwater Bungalows', emoji: '🏠', type: 'Accommodation' },
      { name: 'Bioluminescent Beach', emoji: '✨', type: 'Nature' },
      { name: 'Maafushi Island', emoji: '🏝️', type: 'Beach' },
    ],
    activities: ['Snorkelling & diving', 'Sunset dolphin cruise', 'Sandbank picnic', 'Water sports', 'Island hopping', 'Spa overwater treatment'],
    bestFor: ['Honeymoon', 'Beaches', 'Snorkelling', 'Luxury', 'Romance'],
  },
  lisbon: {
    country: 'Portugal', flag: '🇵🇹',
    attractions: [
      { name: 'Jerónimos Monastery', emoji: '⛪', type: 'Heritage' },
      { name: 'Belém Tower', emoji: '🏰', type: 'Heritage' },
      { name: 'Alfama District', emoji: '🏘️', type: 'Heritage' },
      { name: 'Sintra Palaces', emoji: '🏰', type: 'Heritage' },
      { name: 'LX Factory', emoji: '🛍️', type: 'Culture' },
    ],
    activities: ['Fado music show', 'Tram 28 ride', 'Pastéis de Belém tasting', 'Sintra day trip', 'Wine bar hop in Bairro Alto', 'Azulejo tile workshop'],
    bestFor: ['Culture', 'Food', 'History', 'Nightlife', 'Budget'],
  },
  prague: {
    country: 'Czech Republic', flag: '🇨🇿',
    attractions: [
      { name: 'Prague Castle', emoji: '🏰', type: 'Heritage' },
      { name: 'Charles Bridge', emoji: '🌉', type: 'Landmark' },
      { name: 'Old Town Square & Clock', emoji: '🕰️', type: 'Heritage' },
      { name: 'Josefov Jewish Quarter', emoji: '🕍', type: 'Heritage' },
      { name: 'Wenceslas Square', emoji: '🏙️', type: 'Landmark' },
    ],
    activities: ['Czech beer tasting tour', 'Black light theatre show', 'Boat trip on the Vltava', 'Day trip to Český Krumlov', 'Bohemian countryside wine tour', 'Escape room'],
    bestFor: ['History', 'Beer', 'Budget', 'Architecture', 'Nightlife'],
  },
  santorini: {
    country: 'Greece', flag: '🇬🇷',
    attractions: [
      { name: 'Oia Sunset Viewpoint', emoji: '🌅', type: 'Landmark' },
      { name: 'Akrotiri Archaeological Site', emoji: '🏛️', type: 'Heritage' },
      { name: 'Red Beach', emoji: '🏖️', type: 'Beach' },
      { name: 'Fira Town', emoji: '🏘️', type: 'Landmark' },
      { name: 'Caldera Views', emoji: '🌋', type: 'Nature' },
    ],
    activities: ['Catamaran sunset cruise', 'Volcanic island boat tour', 'Wine tasting (Assyrtiko)', 'Hiking Fira to Oia', 'Cooking class', 'Hot springs swimming'],
    bestFor: ['Romance', 'Sunsets', 'Beaches', 'Wine', 'Honeymoon'],
  },
  istanbul: {
    country: 'Turkey', flag: '🇹🇷',
    attractions: [
      { name: 'Hagia Sophia', emoji: '🕌', type: 'Heritage' },
      { name: 'Blue Mosque', emoji: '🕌', type: 'Heritage' },
      { name: 'Grand Bazaar', emoji: '🛍️', type: 'Market' },
      { name: 'Topkapi Palace', emoji: '🏰', type: 'Heritage' },
      { name: 'Bosphorus Strait', emoji: '⛵', type: 'Landmark' },
    ],
    activities: ['Bosphorus cruise', 'Turkish bath (hamam)', 'Street food tour', 'Whirling dervishes show', 'Spice Bazaar visit', 'Sailing to Prince Islands'],
    bestFor: ['History', 'Food', 'Culture', 'Shopping', 'Architecture'],
  },
  algarve: {
    country: 'Portugal', flag: '🇵🇹',
    attractions: [
      { name: 'Ponta da Piedade Cliffs', emoji: '⛰️', type: 'Nature' },
      { name: 'Benagil Cave', emoji: '🌊', type: 'Nature' },
      { name: 'Praia da Marinha', emoji: '🏖️', type: 'Beach' },
      { name: 'Sagres Fortress', emoji: '🏰', type: 'Heritage' },
      { name: 'Praia da Rocha', emoji: '🏖️', type: 'Beach' },
    ],
    activities: ['Sea cave kayaking', 'Cliff coasteering', 'Water park (Slide & Splash)', 'Mini-golf', 'Boat trip to grottos', 'Jeep safari'],
    bestFor: ['Families', 'Beaches', 'Watersports', 'Budget', 'Outdoors'],
  },
  cairo: {
    country: 'Egypt', flag: '🇪🇬',
    attractions: [
      { name: 'Pyramids of Giza', emoji: '🔺', type: 'Heritage' },
      { name: 'Sphinx', emoji: '🦁', type: 'Heritage' },
      { name: 'Egyptian Museum', emoji: '🏛️', type: 'Museum' },
      { name: 'Khan el-Khalili Bazaar', emoji: '🛍️', type: 'Market' },
      { name: 'Coptic Cairo', emoji: '⛪', type: 'Heritage' },
    ],
    activities: ['Camel ride at pyramids', 'Sound & light show at Giza', 'Nile felucca boat ride', 'Bazaar haggling', 'Day trip to Luxor', 'Sahara desert overnight'],
    bestFor: ['History', 'Budget', 'Adventure', 'Photography', 'Culture'],
  },
};

// ── Fallback generic info when city is not in curated data ───────────────────
function getFallbackInfo(city: string): DestinationInfo {
  return {
    country: '',
    flag: '🌍',
    attractions: [
      { name: 'City Centre', emoji: '🏙️', type: 'Landmark' },
      { name: 'Local Museum', emoji: '🏛️', type: 'Museum' },
      { name: 'Cultural Heritage Site', emoji: '🏛️', type: 'Heritage' },
      { name: 'Local Market', emoji: '🛍️', type: 'Market' },
    ],
    activities: ['Guided city tour', 'Local food tasting', 'Cultural excursion', 'Photography walk', 'Nature hike'],
    bestFor: ['Culture', 'Food', 'Exploration'],
  };
}

function getPhotoUrl(city: string): string {
  const key = city.toLowerCase().trim();
  const id = CITY_PHOTO_IDS[key];
  if (id) return `https://images.unsplash.com/photo-${id}?w=800&q=80&auto=format&fit=crop`;
  return `https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800&q=80&auto=format&fit=crop`;
}

function getDestinationInfo(city: string): DestinationInfo {
  const key = city.toLowerCase().trim();
  return DESTINATION_DATA[key] ?? getFallbackInfo(city);
}

function buildLinks(city: string) {
  const encoded = encodeURIComponent(city);
  return [
    {
      label: 'Google Maps',
      emoji: '🗺️',
      url: `https://www.google.com/maps/search/${encoded}`,
      color: 'text-green-400',
    },
    {
      label: 'TripAdvisor',
      emoji: '🦉',
      url: `https://www.tripadvisor.com/Search?q=${encoded}`,
      color: 'text-emerald-400',
    },
    {
      label: 'Booking.com',
      emoji: '🏨',
      url: `https://www.booking.com/searchresults.html?ss=${encoded}`,
      color: 'text-blue-400',
    },
    {
      label: 'Wikipedia',
      emoji: '📖',
      url: `https://en.wikipedia.org/wiki/${city.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('_')}`,
      color: 'text-gray-300',
    },
  ];
}

// ── Single Destination Card ───────────────────────────────────────────────────
function SingleCard({ city }: { city: string }) {
  const [tab, setTab] = useState<'attractions' | 'activities' | 'links'>('attractions');
  const info = getDestinationInfo(city);
  const photoUrl = getPhotoUrl(city);
  const links = buildLinks(city);
  const displayName = city.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden border border-white/10 bg-slate-900/80 backdrop-blur-md shadow-xl min-w-[260px] max-w-[300px] flex-shrink-0"
    >
      {/* Photo Header */}
      <div className="relative h-36 overflow-hidden">
        <img
          src={photoUrl}
          alt={displayName}
          className="w-full h-full object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).src =
              'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800&q=80&auto=format&fit=crop';
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/30 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <div className="flex items-end justify-between">
            <div>
              <h4 className="font-bold text-white text-base leading-tight flex items-center gap-1.5">
                <MapPin className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                {displayName}
              </h4>
              {info.country && (
                <p className="text-xs text-gray-300 mt-0.5">
                  {info.flag} {info.country}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Best-for chips on photo */}
        <div className="absolute top-2 right-2 flex flex-wrap gap-1 justify-end max-w-[120px]">
          {info.bestFor.slice(0, 2).map(tag => (
            <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded-full bg-black/50 backdrop-blur-sm text-emerald-300 border border-emerald-500/30">
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/10 text-xs">
        {([
          { id: 'attractions', label: 'Sights', icon: <Camera className="w-3 h-3" /> },
          { id: 'activities',  label: 'Activities', icon: <Zap className="w-3 h-3" /> },
          { id: 'links',       label: 'Links', icon: <Link2 className="w-3 h-3" /> },
        ] as const).map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2 transition-colors ${
              tab === t.id
                ? 'text-emerald-400 border-b-2 border-emerald-400 bg-emerald-400/5'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="p-3 min-h-[130px]">
        <AnimatePresence mode="wait">
          {tab === 'attractions' && (
            <motion.ul
              key="attractions"
              initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
              className="space-y-1.5"
            >
              {info.attractions.slice(0, 4).map(a => (
                <li key={a.name} className="flex items-center gap-2 text-xs">
                  <span className="text-base leading-none">{a.emoji}</span>
                  <span className="text-gray-200 flex-1">{a.name}</span>
                  <span className="text-[10px] text-gray-500 bg-white/5 px-1.5 py-0.5 rounded-full">{a.type}</span>
                </li>
              ))}
            </motion.ul>
          )}

          {tab === 'activities' && (
            <motion.div
              key="activities"
              initial={{ opacity: 0, x: 6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
              className="flex flex-wrap gap-1.5"
            >
              {info.activities.map(act => (
                <span
                  key={act}
                  className="text-[11px] px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-gray-300 hover:border-emerald-500/40 hover:text-emerald-300 transition-colors cursor-default"
                >
                  {act}
                </span>
              ))}
            </motion.div>
          )}

          {tab === 'links' && (
            <motion.div
              key="links"
              initial={{ opacity: 0, x: 6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
              className="grid grid-cols-2 gap-2"
            >
              {links.map(link => (
                <a
                  key={link.label}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-[11px] px-2.5 py-2 rounded-xl bg-white/5 border border-white/10 hover:border-emerald-500/40 hover:bg-white/10 transition-all group"
                >
                  <span className="text-sm">{link.emoji}</span>
                  <span className={`${link.color} group-hover:text-white transition-colors truncate`}>{link.label}</span>
                  <ExternalLink className="w-2.5 h-2.5 text-gray-600 group-hover:text-gray-400 ml-auto flex-shrink-0" />
                </a>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ── Multi-card strip with prev/next navigation ────────────────────────────────
interface DestinationMiniCardProps {
  destinations: string[];
}

export default function DestinationMiniCard({ destinations }: DestinationMiniCardProps) {
  const [offset, setOffset] = useState(0);
  if (!destinations || destinations.length === 0) return null;

  // Deduplicate (case-insensitive)
  const seen = new Set<string>();
  const unique = destinations.filter(d => {
    const k = d.toLowerCase().trim();
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  const canPrev = offset > 0;
  const canNext = offset + 2 < unique.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="mt-3 ml-13"
    >
      {/* Section label */}
      <div className="flex items-center justify-between mb-2 px-1">
        <p className="text-xs text-gray-500 flex items-center gap-1">
          <MapPin className="w-3 h-3 text-emerald-500" />
          Destination highlights
        </p>
        {unique.length > 2 && (
          <div className="flex gap-1">
            <button
              onClick={() => setOffset(o => Math.max(0, o - 1))}
              disabled={!canPrev}
              className="p-1 rounded-lg hover:bg-white/10 disabled:opacity-30 transition-all"
            >
              <ChevronLeft className="w-3.5 h-3.5 text-gray-400" />
            </button>
            <button
              onClick={() => setOffset(o => Math.min(unique.length - 1, o + 1))}
              disabled={!canNext}
              className="p-1 rounded-lg hover:bg-white/10 disabled:opacity-30 transition-all"
            >
              <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
            </button>
          </div>
        )}
      </div>

      {/* Card strip */}
      <div className="flex gap-3 overflow-visible">
        <AnimatePresence mode="popLayout">
          {unique.slice(offset, offset + 2).map(city => (
            <SingleCard key={city} city={city} />
          ))}
        </AnimatePresence>
      </div>

      {/* Dot indicators */}
      {unique.length > 2 && (
        <div className="flex gap-1 mt-2 px-1">
          {unique.map((_, i) => (
            <button
              key={i}
              onClick={() => setOffset(Math.min(i, unique.length - 1))}
              className={`h-1 rounded-full transition-all ${
                i >= offset && i < offset + 2
                  ? 'bg-emerald-400 w-4'
                  : 'bg-white/20 w-1.5'
              }`}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
