// Mirrors backend Pydantic models (backend/app/**/schemas.py). Keep in sync with docs/API.md.

export type Money = { amount: number; currency: string };
export type Page<T> = { items: T[]; total: number; page: number; limit: number; has_more: boolean };

export type MediaImage = {
  url: string;
  thumbnail_url?: string | null;
  width?: number | null;
  height?: number | null;
  alt: string;
  attribution: string;
  source: string;
  source_url?: string | null;
};
export type VideoLink = { title: string; url: string; thumbnail_url?: string | null; channel?: string | null; source: string };
export type Place = { name: string; country?: string | null; country_code?: string | null; region?: string | null; lat: number; lng: number; timezone?: string | null };
export type WeatherCondition = "clear" | "partly_cloudy" | "cloudy" | "fog" | "drizzle" | "rain" | "snow" | "storm" | "unknown";
export type WeatherDay = {
  date: string;
  temp_min_c?: number | null;
  temp_max_c?: number | null;
  precipitation_mm?: number | null;
  precipitation_probability?: number | null;
  condition: WeatherCondition;
};

export type TravelStyle = "backpacker" | "budget" | "comfort" | "luxury";
export type TripPace = "relaxed" | "moderate" | "packed";

export type UserPreferences = {
  home_city?: string | null;
  home_airport?: string | null;
  currency: string;
  language: string;
  travel_style: TravelStyle;
  dietary: string[];
  interests: string[];
  notifications_enabled: boolean;
};
export type User = { id: string; email: string; name: string; avatar_url?: string | null; preferences: UserPreferences; created_at: string };
export type TokenPair = { access_token: string; refresh_token: string; token_type: string; expires_in: number };
export type AuthResponse = { user: User; tokens: TokenPair };

export type TravelerInfo = {
  type?: "adult" | "child" | "infant";
  title?: "mr" | "ms" | "mrs" | "miss" | "dr" | null;
  given_name: string;
  family_name: string;
  born_on?: string | null;
  gender?: "m" | "f" | "x" | null;
  email?: string | null;
  phone?: string | null;
  nationality?: string | null;
  passport_number?: string | null;
  passport_expiry?: string | null;
};
export type Traveler = TravelerInfo & { id: string; label: string; created_at: string };

// ─── Trips ──────────────────────────────────────────
export type TripStatus = "draft" | "queued" | "generating" | "ready" | "failed";
export type TripProgress = { status: TripStatus; step: string; percent: number; message: string; updated_at?: string | null };

export type ItineraryItem = {
  time_of_day: "morning" | "afternoon" | "evening" | "night";
  start_time?: string | null;
  title: string;
  description: string;
  place_name: string;
  kind: "activity" | "meal" | "transport" | "rest" | "hotel";
  estimated_cost?: number | null;
  duration_hours?: number | null;
  maps_url?: string | null;
  image?: MediaImage | null;
};
export type DayPlan = { day: number; date?: string | null; title: string; items: ItineraryItem[]; notes: string; weather?: WeatherDay | null };
export type Attraction = {
  name: string;
  description: string;
  area: string;
  category: string;
  estimated_cost?: number | null;
  visit_duration_hours?: number | null;
  best_time: string;
  booking_required: boolean;
  maps_url?: string | null;
  images: MediaImage[];
  videos: VideoLink[];
};
export type HotelSuggestion = {
  name: string;
  area: string;
  description: string;
  price_per_night?: number | null;
  rating?: number | null;
  amenities: string[];
  why: string;
  maps_url?: string | null;
  images: MediaImage[];
  search_hint?: Record<string, unknown> | null;
};
export type RestaurantSuggestion = {
  name: string;
  cuisine: string;
  area: string;
  description: string;
  price_level?: number | null;
  avg_cost_per_person?: number | null;
  must_try: string[];
  dietary_options: string[];
  maps_url?: string | null;
};
export type BudgetLine = { category: "accommodation" | "food" | "activities" | "local_transport" | "misc"; amount: number; note: string };
export type BudgetBreakdown = {
  currency: string;
  total: number;
  per_person: number;
  per_day: number;
  lines: BudgetLine[];
  budget_limit?: number | null;
  within_budget?: boolean | null;
  tips: string[];
};
export type LocalInfo = {
  language: string;
  currency: string;
  timezone: string;
  emergency_numbers: string[];
  best_time_to_visit: string;
  getting_around: string;
  etiquette: string[];
};
export type TripPlan = {
  summary: string;
  highlights: string[];
  location?: Place | null;
  cover_image?: MediaImage | null;
  gallery: MediaImage[];
  videos: VideoLink[];
  days: DayPlan[];
  attractions: Attraction[];
  hotels: HotelSuggestion[];
  restaurants: RestaurantSuggestion[];
  local_dishes: string[];
  budget?: BudgetBreakdown | null;
  local_info?: LocalInfo | null;
  packing_list: string[];
  travel_tips: string[];
  weather: WeatherDay[];
  generation_ms?: number | null;
};
export type TripInputs = {
  title?: string | null;
  destination: string;
  origin?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  duration_days?: number | null;
  travelers?: { adults: number; children: number; infants: number };
  budget?: { amount: number; currency: string; flexible?: boolean } | null;
  travel_style?: TravelStyle;
  pace?: TripPace;
  vibes?: string[];
  interests?: string[];
  dietary?: string[];
  additional_info?: string;
};
export type Trip = Required<Pick<TripInputs, "destination">> &
  TripInputs & {
    id: string;
    title: string;
    duration_days: number;
    travelers: { adults: number; children: number; infants: number };
    travel_style: TravelStyle;
    pace: TripPace;
    status: TripStatus;
    progress: TripProgress;
    plan?: TripPlan | null;
    plan_version: number;
    error?: string | null;
    is_shared: boolean;
    created_at: string;
    updated_at: string;
  };
export type TripSummary = Pick<Trip, "id" | "title" | "destination" | "start_date" | "end_date" | "duration_days" | "status" | "travel_style" | "created_at" | "updated_at"> & {
  cover_image?: MediaImage | null;
};
export type TripMessage = { id: string; role: "user" | "assistant"; content: string; plan_version?: number | null; created_at: string };
export type TripChatResponse = { reply: TripMessage; plan_updated: boolean; trip: Trip };

// ─── Search / offers ────────────────────────────────
export type OfferKind = "flight" | "hotel" | "train" | "bus" | "activity";
type BaseOffer = { offer_id: string; kind: OfferKind; provider: string; title: string; price: Money; refundable: boolean; expires_at?: string | null; deep_link?: string | null };
export type FlightSegment = { carrier: string; carrier_code: string; flight_number: string; origin: string; destination: string; departure_at: string; arrival_at: string };
export type FlightSlice = { origin: string; destination: string; departure_at: string; arrival_at: string; duration_minutes: number; stops: number; segments: FlightSegment[] };
export type FlightOffer = BaseOffer & { kind: "flight"; slices: FlightSlice[]; cabin_class: string; passengers: number; baggage?: string | null };
export type HotelOffer = BaseOffer & {
  kind: "hotel";
  hotel_id: string;
  name: string;
  address: string;
  city: string;
  star_rating?: number | null;
  review_score?: number | null;
  images: MediaImage[];
  room_name: string;
  board_type: string;
  check_in: string;
  check_out: string;
  nights: number;
  price_per_night: Money;
  amenities: string[];
  cancellation_policy?: string | null;
};
export type TransportOffer = BaseOffer & {
  kind: "train" | "bus";
  operator: string;
  service_number: string;
  service_name: string;
  origin: string;
  destination: string;
  departure_at: string;
  arrival_at: string;
  duration_minutes: number;
  travel_class: string;
  seats_available?: number | null;
  amenities: string[];
};
export type ActivityOffer = BaseOffer & {
  kind: "activity";
  product_code: string;
  name: string;
  description: string;
  duration_minutes?: number | null;
  rating?: number | null;
  review_count?: number | null;
  images: MediaImage[];
};
export type AnyOffer = FlightOffer | HotelOffer | TransportOffer | ActivityOffer;
export type SearchResponse<T> = { kind: OfferKind; provider: string; count: number; results: T[]; cached: boolean; searched_at: string };
export type Airport = { iata_code: string; name: string; city: string; country_code: string };

// ─── Bookings ───────────────────────────────────────
export type BookingStatus = "awaiting_confirmation" | "processing" | "confirmed" | "failed" | "cancelled" | "expired";
export type Booking = {
  id: string;
  status: BookingStatus;
  kind: OfferKind;
  provider: string;
  offer: AnyOffer;
  price: Money;
  original_price?: Money | null;
  price_changed: boolean;
  travelers: TravelerInfo[];
  contact?: { email: string; phone: string } | null;
  trip_id?: string | null;
  provider_reference?: string | null;
  tickets: string[];
  payment?: { intent_id: string; provider: string; status: string; amount: Money; client_secret?: string | null } | null;
  confirm_before?: string | null;
  failure_reason?: string | null;
  created_at: string;
  confirmed_at?: string | null;
  cancelled_at?: string | null;
};
export type BookingSummary = { id: string; status: BookingStatus; kind: OfferKind; title: string; price: Money; provider_reference?: string | null; trip_id?: string | null; created_at: string };

// ─── Explore / assistant ────────────────────────────
export type DestinationOverview = {
  query: string;
  place?: Place | null;
  summary?: { title: string; summary: string; url?: string | null } | null;
  images: MediaImage[];
  videos: VideoLink[];
  weather: WeatherDay[];
  maps_url: string;
};
export type AssistantAction =
  | { type: "show_offers"; data: { kind: OfferKind; total: number; results: AnyOffer[] } }
  | { type: "trip_created"; data: { trip_id: string; status: TripStatus; destination: string } }
  | { type: "trip_updated"; data: { trip_id: string; plan_updated: boolean; plan_version: number } }
  | { type: "booking_quote"; data: { booking_id: string; requires_confirmation: true; price: Money; confirm_before?: string | null } }
  | { type: "needs_info"; data: { missing: string[]; intent?: string } };
export type AssistantMessage = { id: string; role: "user" | "assistant"; content: string; intent?: string | null; actions: AssistantAction[]; created_at: string };
export type AssistantReply = { conversation_id: string; message: AssistantMessage; transcript?: string | null };

export type ApiErrorBody = { error: { code: string; message: string; details?: unknown } };
