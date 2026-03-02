'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion';
import { api } from '@/services/api';
import {
  Sparkles,
  MapPin,
  Calendar,
  Users,
  Wallet,
  Plane,
  Zap,
  ArrowRight,
  Play,
  Star,
  Globe,
  Heart,
  Shield,
  Clock,
  ChevronRight,
  Menu,
  X,
} from 'lucide-react';

// Trending destinations data
const trendingDestinations = [
  {
    id: 'tokyo',
    name: 'Tokyo, Japan',
    image_url: 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?q=80&w=800&auto=format&fit=crop',
    vibe_tag: 'Neon & Tradition',
    description: 'Experience the perfect blend of futuristic tech and ancient temples.',
    rating: 4.9,
    price: '$$$',
  },
  {
    id: 'santorini',
    name: 'Santorini, Greece',
    image_url: 'https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?q=80&w=800&auto=format&fit=crop',
    vibe_tag: 'Sun & Sea',
    description: 'White-washed buildings, blue domes, and breathtaking sunsets.',
    rating: 4.8,
    price: '$$$$',
  },
  {
    id: 'iceland',
    name: 'Iceland',
    image_url: 'https://images.unsplash.com/photo-1476610182048-b716b8518aae?q=80&w=800&auto=format&fit=crop',
    vibe_tag: 'Adventure',
    description: 'Chase the Northern Lights and explore dramatic landscapes.',
    rating: 4.9,
    price: '$$$$',
  },
  {
    id: 'bali',
    name: 'Bali, Indonesia',
    image_url: 'https://images.unsplash.com/photo-1537996194471-e657df975ab4?q=80&w=800&auto=format&fit=crop',
    vibe_tag: 'Tropical Paradise',
    description: 'Ancient temples, lush rice terraces, and pristine beaches.',
    rating: 4.7,
    price: '$$',
  },
  {
    id: 'dubai',
    name: 'Dubai, UAE',
    image_url: 'https://images.unsplash.com/photo-1512453979798-5ea904ac6605?q=80&w=800&auto=format&fit=crop',
    vibe_tag: 'Luxury & Innovation',
    description: 'Ultra-modern architecture, luxury shopping, and desert adventures.',
    rating: 4.8,
    price: '$$$$',
  },
  {
    id: 'patagonia',
    name: 'Patagonia, Argentina',
    image_url: 'https://images.unsplash.com/photo-1518182170546-0766ce6fec56?q=80&w=800&auto=format&fit=crop',
    vibe_tag: 'Wild & Free',
    description: 'Pristine wilderness, towering peaks, and glacial lakes.',
    rating: 4.9,
    price: '$$$',
  },
];

// Features
const features = [
  {
    icon: Sparkles,
    title: 'AI-Powered Planning',
    description: 'Our advanced AI learns your preferences to craft perfect itineraries tailored just for you.',
    gradient: 'from-emerald-400 to-cyan-500',
  },
  {
    icon: Globe,
    title: 'Real-Time Insights',
    description: 'Get up-to-date information on weather, events, visa requirements, and travel advisories.',
    gradient: 'from-blue-400 to-purple-500',
  },
  {
    icon: Wallet,
    title: 'Smart Budgeting',
    description: 'Optimize your travel budget with AI-driven cost predictions and money-saving tips.',
    gradient: 'from-orange-400 to-pink-500',
  },
  {
    icon: Shield,
    title: 'Travel Safety',
    description: 'Stay informed with real-time safety updates and comprehensive travel insurance options.',
    gradient: 'from-green-400 to-teal-500',
  },
];

// Stats
const stats = [
  { value: '2M+', label: 'Happy Travelers' },
  { value: '150+', label: 'Countries Covered' },
  { value: '500K+', label: 'Itineraries Created' },
  { value: '4.9/5', label: 'User Rating' },
];

// Testimonials
const testimonials = [
  {
    name: 'Sarah Chen',
    avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=100&auto=format&fit=crop',
    content: "The AI planned our honeymoon perfectly! Every detail was thought out, from romantic dinners to hidden beaches we'd never have found ourselves.",
    trip: 'Bali & Thailand',
    rating: 5,
  },
  {
    name: 'Marcus Johnson',
    avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=100&auto=format&fit=crop',
    content: "As a solo traveler, safety is my priority. This app gave me detailed safety info and connected me with other travelers. Game-changer!",
    trip: 'Solo Europe Adventure',
    rating: 5,
  },
  {
    name: 'Emily & Tom',
    avatar: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?q=80&w=100&auto=format&fit=crop',
    content: "Planning a family trip with kids was stressful until we found this. The AI considered everything - kid-friendly activities, timing, even nap schedules!",
    trip: 'Japan Family Tour',
    rating: 5,
  },
];

const liveRoutesSeed = [
  { from: 'New York', to: 'Lisbon', trend: '+12%', fare: '$498' },
  { from: 'London', to: 'Tokyo', trend: '-6%', fare: '$721' },
  { from: 'San Francisco', to: 'Bali', trend: '+4%', fare: '$887' },
  { from: 'Chicago', to: 'Rome', trend: '-9%', fare: '$562' },
  { from: 'Boston', to: 'Barcelona', trend: '+7%', fare: '$544' },
];

const journeyFlow = [
  { title: 'Tell Your Vibe', detail: 'Type naturally: budget, mood, travel style.' },
  { title: 'Agent Researches', detail: 'AI runs autonomous destination research in background.' },
  { title: 'Compare Matches', detail: 'Get ranked options with reasons and constraints.' },
  { title: 'Lock Itinerary', detail: 'Generate day-by-day plans and booking checklist.' },
];

export default function Home() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [activeTestimonial, setActiveTestimonial] = useState(0);
  const [liveRoutes, setLiveRoutes] = useState(liveRoutesSeed);
  const [funnelSummary, setFunnelSummary] = useState<{
    totals: Record<string, number>;
    conversion: {
      ready_to_started_pct: number;
      started_to_completed_pct: number;
      completed_to_accepted_pct: number;
    };
  } | null>(null);

  const { scrollYProgress } = useScroll();
  const heroY = useTransform(scrollYProgress, [0, 0.2], [0, 100]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);

  // Mouse tracking for spotlight effect
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Auto-rotate testimonials
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveTestimonial((prev) => (prev + 1) % testimonials.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let mounted = true;
    const loadPulse = async () => {
      try {
        const pulse = await api.getTravelPulse();
        if (!mounted) return;
        if (Array.isArray(pulse.routes) && pulse.routes.length > 0) {
          setLiveRoutes(pulse.routes.slice(0, 5));
        }
      } catch {
        // Keep seeded fallback routes if fetch fails.
      }
    };
    loadPulse();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    const loadFunnel = async () => {
      try {
        const summary = await api.getAnalyticsFunnelSummary();
        if (!mounted) return;
        setFunnelSummary({
          totals: summary.totals || {},
          conversion: summary.conversion || {
            ready_to_started_pct: 0,
            started_to_completed_pct: 0,
            completed_to_accepted_pct: 0,
          },
        });
      } catch {
        // Keep panel hidden if unavailable.
      }
    };
    loadFunnel();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <main className="min-h-screen bg-[#0a0a19] text-white overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        {/* Mesh Gradient Background */}
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-500/30 rounded-full blur-3xl animate-float" />
          <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-cyan-500/30 rounded-full blur-3xl animate-float-delayed" />
          <div className="absolute bottom-1/4 left-1/3 w-96 h-96 bg-emerald-500/30 rounded-full blur-3xl animate-float-slow" />
          <div className="absolute bottom-0 right-1/3 w-96 h-96 bg-pink-500/30 rounded-full blur-3xl animate-float" />
        </div>

        {/* Grid Pattern */}
        <div 
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                             linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: '50px 50px',
          }}
        />

        {/* Spotlight Effect */}
        <div
          className="absolute inset-0 transition-opacity duration-300"
          style={{
            background: `radial-gradient(600px circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(127, 90, 240, 0.1), transparent 40%)`,
          }}
        />
      </div>

      {/* Navigation */}
      <motion.nav 
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className="fixed top-0 left-0 right-0 z-50 px-4 py-4"
      >
        <div className="max-w-7xl mx-auto">
          <div className="glass rounded-full px-6 py-4 flex items-center justify-between">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-xl gradient-aurora flex items-center justify-center">
                <Plane className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold">TravelAI</span>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-8">
              <Link href="/research" className="text-sm text-muted-foreground hover:text-white transition-colors">
                Explore
              </Link>
              <Link href="/city/paris" className="text-sm text-muted-foreground hover:text-white transition-colors">
                Destinations
              </Link>
              <Link href="/travelgenie" className="text-sm text-muted-foreground hover:text-white transition-colors">
                Features
              </Link>
              <Link href="/auto-research" className="text-sm text-muted-foreground hover:text-white transition-colors">
                Pricing
              </Link>
            </div>

            {/* CTA Buttons */}
            <div className="hidden md:flex items-center gap-4">
              <Link href="/chat" className="text-sm font-medium hover:text-white transition-colors">
                Sign In
              </Link>
              <Link 
                href="/chat" 
                className="btn-primary text-sm py-3 px-6"
              >
                Start Planning
              </Link>
            </div>

            {/* Mobile Menu Button */}
            <button 
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="md:hidden p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden mt-4 glass rounded-2xl overflow-hidden"
            >
              <div className="p-4 space-y-4">
                <Link href="/research" className="block py-2 hover:text-white transition-colors">
                  Explore
                </Link>
                <Link href="/city/paris" className="block py-2 hover:text-white transition-colors">
                  Destinations
                </Link>
                <Link href="/travelgenie" className="block py-2 hover:text-white transition-colors">
                  Features
                </Link>
                <Link href="/auto-research" className="block py-2 hover:text-white transition-colors">
                  Pricing
                </Link>
                <div className="pt-4 border-t border-white/10 flex flex-col gap-3">
                  <Link href="/chat" className="text-center py-3 font-medium">
                    Sign In
                  </Link>
                  <Link href="/chat" className="btn-primary text-center py-3">
                    Start Planning
                  </Link>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.nav>

      {/* Hero Section */}
      <motion.section 
        style={{ y: heroY, opacity: heroOpacity }}
        className="relative min-h-screen flex items-center justify-center pt-20"
      >
        {/* Background Video/Image */}
        <div className="absolute inset-0 z-0">
          <div
            className="absolute inset-0 bg-cover bg-center transition-transform duration-[30s] hover:scale-105"
            style={{ 
              backgroundImage: "url('https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?q=80&w=2021&auto=format&fit=crop')",
            }}
          >
            <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/50 to-[#0a0a19]" />
          </div>
        </div>

        {/* Hero Content */}
        <div className="relative z-10 container-modern text-center px-4">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            {/* Badge */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass mb-8"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-sm font-medium">AI-Powered Travel Planning</span>
            </motion.div>

            {/* Main Heading */}
            <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-6">
              Discover Your Next
              <br />
              <span className="text-gradient">Dream Adventure</span>
            </h1>

            {/* Subtitle */}
            <p className="text-lg sm:text-xl text-gray-300 max-w-3xl mx-auto mb-10 leading-relaxed">
              Stop searching, start traveling. Let our AI build your perfect itinerary,
              check visas, monitor weather, and find hidden gems — all in seconds.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
              <Link
                href="/chat"
                className="group relative overflow-hidden rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 px-10 py-5 font-semibold text-white shadow-2xl shadow-emerald-500/30 transition-all hover:scale-105 hover:shadow-emerald-500/50"
              >
                <span className="relative z-10 flex items-center gap-2">
                  Start Planning Now
                  <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
                </span>
              </Link>
              
              <Link
                href="/travelgenie"
                className="group flex items-center gap-2 rounded-full glass px-10 py-5 font-semibold transition-all hover:bg-white/20 hover:scale-105"
              >
                <Play className="w-5 h-5" />
                Watch Demo
              </Link>
            </div>

            {/* Trust Indicators */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
              className="flex flex-wrap justify-center items-center gap-8 text-sm text-gray-400"
            >
              <div className="flex items-center gap-2">
                <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                <span>4.9/5 User Rating</span>
              </div>
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                <span>2M+ Travelers</span>
              </div>
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4" />
                <span>150+ Countries</span>
              </div>
            </motion.div>
          </motion.div>
        </div>

        {/* Scroll Indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <div className="flex flex-col items-center gap-2 text-gray-400">
            <span className="text-sm">Scroll to explore</span>
            <motion.div
              animate={{ y: [0, 8, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="w-6 h-10 rounded-full border-2 border-white/30 flex items-start justify-center p-2"
            >
              <motion.div className="w-1.5 h-1.5 rounded-full bg-white/60" />
            </motion.div>
          </div>
        </motion.div>
      </motion.section>

      {/* Live Travel Pulse */}
      <section className="relative z-10 py-8">
        <div className="container-modern">
          <div className="rounded-3xl border border-white/15 bg-black/30 backdrop-blur-md overflow-hidden">
            <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between">
              <p className="text-sm font-semibold tracking-wide text-cyan-200">Live Travel Pulse</p>
              <p className="text-xs text-gray-400">Routes, price shifts, and trip momentum</p>
            </div>
            <div className="px-5 py-4 grid md:grid-cols-5 gap-3">
              {liveRoutes.map((route, idx) => (
                <motion.div
                  key={`${route.from}-${route.to}`}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.08 }}
                  className="rounded-2xl bg-white/5 border border-white/10 p-3"
                >
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">{route.from}</p>
                  <p className="text-sm font-semibold text-white flex items-center gap-2 mt-1">
                    <Plane className="w-3.5 h-3.5 text-cyan-300" />
                    {route.to}
                  </p>
                  <div className="mt-3 flex items-center justify-between text-xs">
                    <span className="text-emerald-300">{route.fare}</span>
                    <span className={`${route.trend.startsWith('-') ? 'text-emerald-300' : 'text-orange-300'}`}>
                      {route.trend}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Journey Flow */}
      <section className="relative z-10 py-8">
        <div className="container-modern">
          <div className="rounded-3xl glass-card p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-6">
              <h3 className="text-2xl sm:text-3xl font-bold">From Idea To Itinerary</h3>
              <p className="text-sm text-gray-400">A travel-first autonomous planning loop</p>
            </div>
            <div className="grid md:grid-cols-4 gap-4">
              {journeyFlow.map((step, idx) => (
                <motion.div
                  key={step.title}
                  initial={{ opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.08 }}
                  className="rounded-2xl border border-white/10 bg-white/5 p-4"
                >
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 text-[#0a0a19] text-xs font-bold flex items-center justify-center mb-3">
                    {idx + 1}
                  </div>
                  <p className="font-semibold text-white">{step.title}</p>
                  <p className="text-sm text-gray-400 mt-2">{step.detail}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Funnel Summary */}
      {funnelSummary && (
        <section className="relative z-10 py-8">
          <div className="container-modern">
            <div className="rounded-3xl border border-white/15 bg-black/30 backdrop-blur-md p-6">
              <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-5">
                <h3 className="text-2xl font-bold">Autonomous Agent Funnel</h3>
                <p className="text-sm text-gray-400">Live conversion metrics from active usage</p>
              </div>
              <div className="grid md:grid-cols-4 gap-3 mb-4">
                <div className="rounded-2xl bg-white/5 border border-white/10 p-3">
                  <p className="text-xs text-gray-400">Ready Reached</p>
                  <p className="text-2xl font-semibold">{funnelSummary.totals.chat_ready_reached || 0}</p>
                </div>
                <div className="rounded-2xl bg-white/5 border border-white/10 p-3">
                  <p className="text-xs text-gray-400">Research Started</p>
                  <p className="text-2xl font-semibold">{funnelSummary.totals.autonomous_research_started || 0}</p>
                </div>
                <div className="rounded-2xl bg-white/5 border border-white/10 p-3">
                  <p className="text-xs text-gray-400">Research Completed</p>
                  <p className="text-2xl font-semibold">{funnelSummary.totals.autonomous_research_completed || 0}</p>
                </div>
                <div className="rounded-2xl bg-white/5 border border-white/10 p-3">
                  <p className="text-xs text-gray-400">Recommendation Accepted</p>
                  <p className="text-2xl font-semibold">{funnelSummary.totals.recommendation_accepted || 0}</p>
                </div>
              </div>
              <div className="grid md:grid-cols-3 gap-3">
                <div className="rounded-2xl bg-emerald-500/10 border border-emerald-400/20 p-3">
                  <p className="text-xs text-emerald-200">Ready → Started</p>
                  <p className="text-xl font-semibold text-emerald-300">{funnelSummary.conversion.ready_to_started_pct}%</p>
                </div>
                <div className="rounded-2xl bg-cyan-500/10 border border-cyan-400/20 p-3">
                  <p className="text-xs text-cyan-200">Started → Completed</p>
                  <p className="text-xl font-semibold text-cyan-300">{funnelSummary.conversion.started_to_completed_pct}%</p>
                </div>
                <div className="rounded-2xl bg-orange-500/10 border border-orange-400/20 p-3">
                  <p className="text-xs text-orange-200">Completed → Accepted</p>
                  <p className="text-xl font-semibold text-orange-300">{funnelSummary.conversion.completed_to_accepted_pct}%</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Stats Section */}
      <section className="py-20 relative z-10">
        <div className="container-modern">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="text-center"
              >
                <div className="text-4xl sm:text-5xl font-bold text-gradient mb-2">
                  {stat.value}
                </div>
                <div className="text-gray-400">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 relative z-10">
        <div className="container-modern">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-4">
              Why Choose <span className="text-gradient">TravelAI</span>?
            </h2>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">
              Experience the future of travel planning with cutting-edge AI technology
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -8, scale: 1.02 }}
                className="group relative p-6 rounded-3xl glass-card card-hover"
              >
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                  <feature.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-gray-400 leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Trending Destinations */}
      <section className="py-24 relative z-10">
        <div className="container-modern">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="flex items-end justify-between mb-12"
          >
            <div>
              <h2 className="text-4xl sm:text-5xl font-bold mb-4">
                Trending <span className="text-gradient">Now</span>
              </h2>
              <p className="text-xl text-gray-400">
                Discover the most popular destinations this season
              </p>
            </div>
            <Link 
              href="/research" 
              className="hidden sm:flex items-center gap-2 text-emerald-400 hover:text-emerald-300 transition-colors font-medium"
            >
              View all
              <ChevronRight className="w-5 h-5" />
            </Link>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trendingDestinations.map((dest, index) => (
              <motion.div
                key={dest.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -8 }}
                className="group relative h-96 overflow-hidden rounded-3xl cursor-pointer"
              >
                <Image
                  src={dest.image_url}
                  alt={dest.name}
                  fill
                  className="object-cover transition-transform duration-700 group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent" />
                
                {/* Content */}
                <div className="absolute bottom-0 left-0 right-0 p-6">
                  <div className="mb-2 inline-flex items-center gap-2">
                    <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-medium backdrop-blur-sm">
                      {dest.vibe_tag}
                    </span>
                    <span className="flex items-center gap-1 text-yellow-400 text-sm">
                      <Star className="w-4 h-4 fill-yellow-400" />
                      {dest.rating}
                    </span>
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-2">{dest.name}</h3>
                  <p className="text-gray-300 text-sm line-clamp-2 mb-3">{dest.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400 text-sm">{dest.price}</span>
                    <span className="text-emerald-400 text-sm font-medium flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      Explore <ArrowRight className="w-4 h-4" />
                    </span>
                  </div>
                </div>

                {/* Heart Button */}
                <button className="absolute top-4 right-4 w-10 h-10 rounded-full glass flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:scale-110">
                  <Heart className="w-5 h-5" />
                </button>
              </motion.div>
            ))}
          </div>

          <div className="mt-8 text-center sm:hidden">
              <Link 
                href="/research" 
                className="inline-flex items-center gap-2 text-emerald-400 hover:text-emerald-300 transition-colors font-medium"
            >
              View all destinations
              <ChevronRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-24 relative z-10">
        <div className="container-modern">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-4">
              Loved by <span className="text-gradient">Travelers</span>
            </h2>
            <p className="text-xl text-gray-400">
              See what our community has to say
            </p>
          </motion.div>

          <div className="max-w-4xl mx-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTestimonial}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                className="glass-panel text-center"
              >
                <div className="flex justify-center mb-6">
                  {[...Array(testimonials[activeTestimonial].rating)].map((_, i) => (
                    <Star key={i} className="w-6 h-6 text-yellow-400 fill-yellow-400" />
                  ))}
                </div>
                <p className="text-xl sm:text-2xl leading-relaxed mb-8">
                  &ldquo;{testimonials[activeTestimonial].content}&rdquo;
                </p>
                <div className="flex items-center justify-center gap-4">
                  <Image
                    src={testimonials[activeTestimonial].avatar}
                    alt={testimonials[activeTestimonial].name}
                    width={56}
                    height={56}
                    className="rounded-full"
                  />
                  <div className="text-left">
                    <div className="font-semibold">{testimonials[activeTestimonial].name}</div>
                    <div className="text-gray-400 text-sm">{testimonials[activeTestimonial].trip}</div>
                  </div>
                </div>
              </motion.div>
            </AnimatePresence>

            {/* Dots */}
            <div className="flex justify-center gap-2 mt-8">
              {testimonials.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setActiveTestimonial(index)}
                  className={`w-2 h-2 rounded-full transition-all ${
                    index === activeTestimonial 
                      ? 'w-8 bg-emerald-500' 
                      : 'bg-gray-600 hover:bg-gray-500'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 relative z-10">
        <div className="container-modern">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="relative rounded-3xl overflow-hidden"
          >
            {/* Background */}
            <div className="absolute inset-0 gradient-midnight animate-gradient" />
            <div className="absolute inset-0 opacity-30">
              <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-500/30 rounded-full blur-3xl" />
              <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyan-500/30 rounded-full blur-3xl" />
            </div>

            {/* Content */}
            <div className="relative z-10 py-20 px-8 text-center">
              <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6">
                Ready to Start Your Adventure?
              </h2>
              <p className="text-xl text-gray-300 max-w-2xl mx-auto mb-10">
                Join millions of travelers who trust TravelAI to plan their perfect trips
              </p>
              <Link
                href="/chat"
                className="inline-flex items-center gap-2 rounded-full bg-white text-gray-900 px-10 py-5 font-semibold hover:bg-gray-100 transition-colors hover:scale-105"
              >
                <Sparkles className="w-5 h-5" />
                Plan Your Trip Now
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/10 relative z-10">
        <div className="container-modern">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-xl gradient-aurora flex items-center justify-center">
                <Plane className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold">TravelAI</span>
            </div>
            <div className="text-gray-400 text-sm">
              © 2024 TravelAI. All rights reserved.
            </div>
            <div className="flex items-center gap-6 text-sm text-gray-400">
              <Link href="/research" className="hover:text-white transition-colors">Privacy</Link>
              <Link href="/travelgenie" className="hover:text-white transition-colors">Terms</Link>
              <Link href="/chat" className="hover:text-white transition-colors">Contact</Link>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}
