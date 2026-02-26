import axios, { AxiosInstance, AxiosError } from 'axios';
import { 
  TravelRequest, Destination, User, AuthResponse,
  Itinerary, ItinerarySummary, CreateItineraryRequest, CreateActivityRequest
} from '@/types/travel';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async register(email: string, password: string, fullName?: string, passportCountry?: string): Promise<AuthResponse> {
    const response = await this.client.post('/auth/register', {
      email,
      password,
      full_name: fullName,
      passport_country: passportCountry || 'US',
    });
    return response.data;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await this.client.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    
    if (response.data.access_token) {
      localStorage.setItem('token', response.data.access_token);
    }
    
    return response.data;
  }

  logout(): void {
    localStorage.removeItem('token');
  }

  async getMe(): Promise<User> {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  async getPreferences(): Promise<any> {
    const response = await this.client.get('/auth/preferences');
    return response.data;
  }

  async updatePreferences(preferences: any): Promise<any> {
    const response = await this.client.put('/auth/preferences', preferences);
    return response.data;
  }

  // Recommendations
  async getRecommendations(request: TravelRequest): Promise<Destination[]> {
    const response = await this.client.post('/recommendations', request);
    return response.data;
  }

  // Destinations
  async listDestinations(query?: string, country?: string): Promise<any[]> {
    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (country) params.append('country', country);
    
    const response = await this.client.get(`/destinations?${params.toString()}`);
    return response.data;
  }

  async getDestinationDetails(
    destinationId: string,
    travelStart?: string,
    travelEnd?: string,
    passportCountry?: string
  ): Promise<Destination> {
    const params = new URLSearchParams();
    if (travelStart) params.append('travel_start', travelStart);
    if (travelEnd) params.append('travel_end', travelEnd);
    if (passportCountry) params.append('passport_country', passportCountry);
    
    const response = await this.client.get(`/destinations/${destinationId}?${params.toString()}`);
    return response.data;
  }

  // Visa
  async checkVisaRequirements(passportCountry: string, destinationCountry: string): Promise<any> {
    const response = await this.client.get(`/visa-requirements/${passportCountry}/${destinationCountry}`);
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Itineraries
  async createItinerary(data: CreateItineraryRequest): Promise<Itinerary> {
    const response = await this.client.post('/itineraries', data);
    return response.data;
  }

  async listItineraries(): Promise<ItinerarySummary[]> {
    const response = await this.client.get('/itineraries');
    return response.data;
  }

  async listPublicItineraries(): Promise<ItinerarySummary[]> {
    const response = await this.client.get('/itineraries/public');
    return response.data;
  }

  async getItinerary(id: string): Promise<Itinerary> {
    const response = await this.client.get(`/itineraries/${id}`);
    return response.data;
  }

  async updateItinerary(id: string, data: Partial<CreateItineraryRequest>): Promise<Itinerary> {
    const response = await this.client.put(`/itineraries/${id}`, data);
    return response.data;
  }

  async deleteItinerary(id: string): Promise<void> {
    await this.client.delete(`/itineraries/${id}`);
  }

  // Activities
  async addActivity(itineraryId: string, dayId: string, data: CreateActivityRequest): Promise<Itinerary> {
    const response = await this.client.post(`/itineraries/${itineraryId}/days/${dayId}/activities`, data);
    return response.data;
  }

  async updateActivity(
    itineraryId: string, 
    dayId: string, 
    activityId: string, 
    data: Partial<CreateActivityRequest>
  ): Promise<Itinerary> {
    const response = await this.client.put(
      `/itineraries/${itineraryId}/days/${dayId}/activities/${activityId}`, 
      data
    );
    return response.data;
  }

  async deleteActivity(itineraryId: string, dayId: string, activityId: string): Promise<Itinerary> {
    const response = await this.client.delete(
      `/itineraries/${itineraryId}/days/${dayId}/activities/${activityId}`
    );
    return response.data;
  }

  // Auto Research
  async startAutoResearch(preferences: TravelPreferences): Promise<ResearchJob> {
    const response = await this.client.post('/auto-research/start', preferences);
    return response.data;
  }

  async getResearchStatus(jobId: string): Promise<ResearchJob> {
    const response = await this.client.get(`/auto-research/status/${jobId}`);
    return response.data;
  }

  async getResearchResults(jobId: string): Promise<ResearchResults> {
    const response = await this.client.get(`/auto-research/results/${jobId}`);
    return response.data;
  }

  async listResearchJobs(userId?: string, status?: string): Promise<ResearchJob[]> {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (status) params.append('status', status);
    
    const response = await this.client.get(`/auto-research/jobs?${params.toString()}`);
    return response.data;
  }

  async deleteResearchJob(jobId: string): Promise<void> {
    await this.client.delete(`/auto-research/jobs/${jobId}`);
  }

  async getResearchConfig(): Promise<ResearchConfig> {
    const response = await this.client.get('/auto-research/config');
    return response.data;
  }

  // City Details
  async getCityDetails(
    cityName: string, 
    params?: {
      origin?: string;
      travel_start?: string;
      travel_end?: string;
      passport_country?: string;
      budget_level?: string;
    }
  ): Promise<CityDetails> {
    const queryParams = new URLSearchParams();
    if (params?.origin) queryParams.append('origin', params.origin);
    if (params?.travel_start) queryParams.append('travel_start', params.travel_start);
    if (params?.travel_end) queryParams.append('travel_end', params.travel_end);
    if (params?.passport_country) queryParams.append('passport_country', params.passport_country);
    if (params?.budget_level) queryParams.append('budget_level', params.budget_level);
    
    const response = await this.client.get(`/cities/${cityName}/details?${queryParams.toString()}`);
    return response.data;
  }

  async getCityFlights(
    cityName: string,
    origin: string,
    departure_date?: string,
    return_date?: string
  ): Promise<CityFlightsResponse> {
    const params = new URLSearchParams();
    params.append('origin', origin);
    if (departure_date) params.append('departure_date', departure_date);
    if (return_date) params.append('return_date', return_date);
    
    const response = await this.client.get(`/cities/${cityName}/flights?${params.toString()}`);
    return response.data;
  }

  async getCityAttractions(
    cityName: string,
    category?: string,
    interests?: string[]
  ): Promise<CityAttractionsResponse> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (interests) interests.forEach(i => params.append('interests', i));
    
    const response = await this.client.get(`/cities/${cityName}/attractions?${params.toString()}`);
    return response.data;
  }

  async getCityEvents(
    cityName: string,
    start_date?: string,
    end_date?: string
  ): Promise<CityEventsResponse> {
    const params = new URLSearchParams();
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    
    const response = await this.client.get(`/cities/${cityName}/events?${params.toString()}`);
    return response.data;
  }

  async searchCities(query: string): Promise<{ query: string; results: CitySearchResult[] }> {
    const response = await this.client.get(`/cities/search?query=${encodeURIComponent(query)}`);
    return response.data;
  }

  // Agent
  async agentChat(message: string, conversationHistory?: any[], userPreferences?: any): Promise<any> {
    const response = await this.client.post('/agent/chat', {
      message,
      conversation_history: conversationHistory || [],
      user_preferences: userPreferences,
    });
    return response.data;
  }

  async agentResearch(destination: string, interests?: string[]): Promise<any> {
    const response = await this.client.post('/agent/research', { destination, interests: interests || [] });
    return response.data;
  }

  async agentCompare(destinations: string[], criteria?: string[]): Promise<any> {
    const response = await this.client.post('/agent/compare', {
      destinations,
      criteria: criteria || ['affordability', 'activities', 'weather', 'safety'],
    });
    return response.data;
  }

  async agentHiddenGems(region: string, interests?: string[], avoidCrowds?: boolean): Promise<any> {
    const response = await this.client.post('/agent/hidden-gems', {
      region,
      interests: interests || [],
      avoid_crowds: avoidCrowds ?? true,
    });
    return response.data;
  }

  async agentItineraryResearch(destination: string, days: number, interests?: string[], travelStyle?: string): Promise<any> {
    const response = await this.client.post('/agent/itinerary-research', {
      destination,
      days,
      interests: interests || ['culture', 'food', 'nature'],
      travel_style: travelStyle || 'moderate',
    });
    return response.data;
  }
}

export const api = new ApiService();

// Types for Auto Research
export interface TravelPreferences {
  origin?: string;
  destinations?: string[];
  travel_start?: string;
  travel_end?: string;
  budget_level?: 'low' | 'moderate' | 'high' | 'luxury';
  budget_amount?: number;
  interests?: string[];
  traveling_with?: 'solo' | 'couple' | 'family' | 'group';
  passport_country?: string;
  visa_preference?: 'visa_free' | 'visa_on_arrival' | 'evisa_ok';
  weather_preference?: 'hot' | 'warm' | 'mild' | 'cold' | 'snow';
  max_flight_duration?: number;
  accessibility_needs?: string[];
  dietary_restrictions?: string[];
  notes?: string;
  // New fields
  has_kids?: boolean;
  kids_count?: number;
  kids_ages?: string[];
  trip_type?: 'leisure' | 'adventure' | 'cultural' | 'romantic' | 'family' | 'business' | 'food' | 'wellness';
  pace_preference?: 'relaxed' | 'moderate' | 'busy';
}

export interface ResearchJob {
  job_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress_percentage: number;
  current_step: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  destinations_count: number;
  results_available: boolean;
}

export interface ResearchResults {
  job_id: string;
  status: string;
  preferences: TravelPreferences;
  research_timestamp: string;
  destinations: ResearchDestination[];
  comparison?: ResearchComparison;
  recommendations: ResearchRecommendation[];
}

export interface ResearchDestination {
  name: string;
  status: string;
  overall_score?: number;
  error?: string;
  data: {
    weather?: any;
    visa?: any;
    attractions?: any[];
    events?: any[];
    affordability?: any;
    flights?: any[];
    hotels?: any[];
    web_research?: any;
  };
}

export interface ResearchComparison {
  categories: string[];
  destinations: Array<{
    name: string;
    overall_score: number;
    weather: any;
    visa_required: boolean;
    attractions_count: number;
    budget_fit: string;
    events_count: number;
  }>;
}

export interface ResearchRecommendation {
  rank: number;
  destination: string;
  score: number;
  reasons: string[];
  highlights: {
    top_attractions?: string[];
    top_events?: string[];
    hotel_from?: number;
    flight_from?: number;
  };
  estimated_cost?: any;
}

export interface ResearchConfig {
  budget_levels: string[];
  travel_styles: string[];
  visa_preferences: string[];
  weather_preferences: string[];
  interests: string[];
  max_flight_duration_options: number[];
}

// City Details Types
export interface CityDetails {
  overview: CityOverview;
  weather: CityWeather;
  flights: CityFlights;
  attractions: CityAttractions;
  events: CityEvents;
  hotels: CityHotels;
  restaurants: CityRestaurants;
  transport: CityTransport;
  costs: CityCosts;
  visa: CityVisa;
  tips: string[];
  weather_alerts: string[];
  images: {
    hero: string;
    gallery: string[];
    attractions: Record<string, string>;
  };
}

export interface CityOverview {
  name: string;
  country: string;
  description: string;
  best_time_to_visit: string;
  language: string;
  currency: string;
  time_zone: string;
  emergency_number: string;
}

export interface CityWeather {
  current_temp: number | null;
  condition: string;
  humidity: number | null;
  forecast: Array<{
    day: string;
    temp: number;
    condition: string;
  }>;
  best_time_to_visit: string;
  climate_overview: string;
}

export interface CityFlights {
  from_origin: string | null;
  cheapest_price: number | null;
  duration_hours: number | null;
  airlines: string[];
  flight_options: Array<{
    airline: string;
    price: number;
    duration_hours: number;
    departure_time: string;
    arrival_time: string;
    stops: number;
  }>;
}

export interface CityAttractions {
  top_attractions: Array<{
    name: string;
    description: string;
    category: string;
    rating: number;
    price_level: string;
    location?: {
      lat: number;
      lon: number;
    };
  }>;
  categories: string[];
  total_count: number;
}

export interface CityEvents {
  upcoming_events: Array<{
    name: string;
    date: string;
    type: string;
    description: string;
  }>;
  festivals: Array<{
    name: string;
    date: string;
    type: string;
    description: string;
  }>;
  total_count: number;
}

export interface CityHotels {
  price_range: {
    min: number;
    max: number;
  };
  top_rated: Array<{
    name: string;
    rating: number;
    price_per_night: number;
    location: string;
  }>;
  budget_options: Array<{
    name: string;
    rating: number;
    price_per_night: number;
    location: string;
  }>;
  luxury_options: Array<{
    name: string;
    rating: number;
    price_per_night: number;
    location: string;
  }>;
}

export interface CityRestaurants {
  must_try_dishes: string[];
  top_restaurants: Array<{
    name: string;
    cuisine: string;
    rating: number;
    price_range: string;
    description: string;
  }>;
  food_scene: string;
  price_range: string;
}

export interface CityTransport {
  from_airport: {
    options: string[];
    recommended: string;
    cost_range: string;
  };
  public_transport: {
    available: boolean;
    types: string[];
    cost_per_ride: string;
    day_pass: string;
  };
  taxi_rideshare: {
    available: boolean;
    apps: string[];
    base_fare: string;
  };
  recommended_pass: string;
  metro_lines?: Array<{
    line: string;
    color: string;
    route: string;
    key_stops: string[];
  }>;
  bus_network?: {
    coverage: string;
    day_hours: string;
    night_hours: string;
    key_routes: string[];
    cost: string;
  };
  cab_companies?: Array<{
    name: string;
    phone?: string;
    app?: string;
    features: string;
  }>;
  bike_scooter?: {
    vlib?: string;
    santander?: string;
    citi_bike?: string;
    rental?: string;
    docomo?: string;
    lime_tier?: string;
    lime?: string;
    revel?: string;
    gojek_bike?: string;
    notes?: string;
  };
  walking_info?: {
    walkability: string;
    pedestrian_zones?: string;
    walking_tours?: string;
    notes?: string;
  };
  transport_apps?: string[];
  payment_methods?: string[];
}

export interface CityCosts {
  budget_daily: number;
  moderate_daily: number;
  luxury_daily: number;
  meal_average: number;
  transport_average: number;
}

export interface CityVisa {
  visa_required: boolean;
  visa_type: string | null;
  duration: string | null;
  cost: string | null;
  processing_time: string | null;
}

export interface CitySearchResult {
  name: string;
  country: string;
  description: string;
  best_time: string;
}

export interface CityFlightsResponse {
  city: string;
  origin: string;
  flights: CityFlights['flight_options'];
  cheapest: number | null;
  airlines: string[];
}

export interface CityAttractionsResponse {
  city: string;
  attractions: CityAttractions['top_attractions'];
  total: number;
  categories: string[];
}

export interface CityEventsResponse {
  city: string;
  events: CityEvents['upcoming_events'];
  total: number;
  date_range: {
    start: string | null;
    end: string | null;
  };
}
