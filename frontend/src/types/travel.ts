export interface TravelRequest {
  origin: string;
  travel_start: string;
  travel_end: string;
  num_travelers: number;
  num_recommendations: number;
  user_preferences: UserPreferences;
}

export interface UserPreferences {
  budget_daily: number;
  budget_total: number;
  travel_style: 'budget' | 'moderate' | 'comfort' | 'luxury';
  interests: Interest[];
  preferred_weather?: string;
  avoid_weather?: string;
  passport_country: string;
  visa_preference: string;
  max_flight_duration?: number;
  traveling_with: 'solo' | 'couple' | 'family' | 'friends';
  accessibility_needs: string[];
  dietary_restrictions: string[];
  // Location preferences
  preferred_continent?: string;
  preferred_countries: string[];
}

export type TravelStyle = 'budget' | 'moderate' | 'comfort' | 'luxury';

export type Interest = 
  | 'nature' 
  | 'culture' 
  | 'adventure' 
  | 'relaxation' 
  | 'food' 
  | 'nightlife' 
  | 'shopping' 
  | 'history' 
  | 'art' 
  | 'beaches' 
  | 'mountains' 
  | 'wildlife';

export interface Destination {
  id: string;
  name: string;
  country: string;
  city: string;
  country_code: string;
  coordinates: {
    lat: number;
    lng: number;
  };
  description?: string;
  image_url?: string;
  
  // Enriched data
  weather?: Weather;
  affordability?: Affordability;
  visa?: Visa;
  attractions: Attraction[];
  events: Event[];
  
  // AI scores
  overall_score: number;
  recommendation_reason: string;
  weather_score: number;
  affordability_score: number;
  visa_score: number;
  attractions_score: number;
  events_score: number;
}

export interface Weather {
  condition: string;
  temperature: number;
  humidity: number;
  wind_speed: number;
  forecast_days: WeatherForecastDay[];
  recommendation: string;
}

export interface WeatherForecastDay {
  date: string;
  temp: number;
  condition: string;
  description: string;
}

export interface Affordability {
  cost_level: 'budget' | 'moderate' | 'expensive' | 'luxury';
  daily_cost_estimate: number;
  currency: string;
  accommodation_avg: number;
  food_avg: number;
  transport_avg: number;
  activities_avg: number;
  cost_index: number;
}

export interface Visa {
  required: boolean;
  type?: string;
  duration_days?: number;
  processing_days?: number;
  cost_usd?: number;
  evisa_available: boolean;
  visa_free_days?: number;
  notes: string;
}

export interface Attraction {
  id: string;
  name: string;
  type: string;
  rating: number;
  description: string;
  image_url?: string;
  location: {
    lat: number;
    lng: number;
  };
  entry_fee?: number;
  currency: string;
  opening_hours?: string;
  duration_hours?: number;
  best_time_to_visit?: string;
  natural_feature: boolean;
}

export interface Event {
  id: string;
  name: string;
  type: 'music' | 'theatre' | 'film' | 'sports' | 'festival' | 'cultural' | 'food' | 'art';
  date: string;
  venue: string;
  description?: string;
  price_range?: string;
  url?: string;
  image_url?: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  passport_country?: string;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Itinerary types
export type ActivityType = 
  | 'attraction' 
  | 'restaurant' 
  | 'event' 
  | 'transport' 
  | 'accommodation' 
  | 'shopping' 
  | 'relaxation' 
  | 'general';

export interface ItineraryActivity {
  id: string;
  day_id: string;
  title: string;
  description?: string;
  activity_type: ActivityType;
  start_time?: string;
  end_time?: string;
  location_name?: string;
  latitude?: number;
  longitude?: number;
  cost: number;
  booking_reference?: string;
  notes?: string;
  created_at: string;
}

export interface ItineraryDay {
  id: string;
  itinerary_id: string;
  day_number: number;
  date: string;
  notes?: string;
  activities: ItineraryActivity[];
}

export interface Itinerary {
  id: string;
  user_id: string;
  title: string;
  destination_id: string;
  destination_name: string;
  destination_country: string;
  travel_start: string;
  travel_end: string;
  notes?: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  days: ItineraryDay[];
}

export interface ItinerarySummary {
  id: string;
  title: string;
  destination_name: string;
  destination_country: string;
  travel_start: string;
  travel_end: string;
  is_public: boolean;
  created_at: string;
  total_days: number;
  total_activities: number;
}

export interface CreateItineraryRequest {
  title: string;
  destination_id: string;
  destination_name: string;
  destination_country: string;
  travel_start: string;
  travel_end: string;
  notes?: string;
  is_public?: boolean;
  days?: CreateItineraryDayRequest[];
}

export interface CreateItineraryDayRequest {
  day_number: number;
  date: string;
  notes?: string;
  activities?: CreateActivityRequest[];
}

export interface CreateActivityRequest {
  title: string;
  description?: string;
  activity_type?: ActivityType;
  start_time?: string;
  end_time?: string;
  location_name?: string;
  latitude?: number;
  longitude?: number;
  cost?: number;
  booking_reference?: string;
  notes?: string;
}