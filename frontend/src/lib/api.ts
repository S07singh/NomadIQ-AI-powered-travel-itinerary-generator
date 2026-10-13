// Typed client for the NomadIQ API v1. Bearer tokens live in localStorage; a 401 triggers one
// refresh-token rotation (shared across concurrent requests) before giving up.

import type {
  AnyOffer,
  ApiErrorBody,
  AssistantMessage,
  AssistantReply,
  AuthResponse,
  Booking,
  BookingSummary,
  DestinationOverview,
  MediaImage,
  Page,
  Place,
  SearchResponse,
  TokenPair,
  Traveler,
  TravelerInfo,
  Trip,
  TripChatResponse,
  TripInputs,
  TripMessage,
  TripProgress,
  TripSummary,
  User,
  UserPreferences,
  Airport,
  Money,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/api/v1";
const TOKENS_KEY = "nomadiq.tokens";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown) {
    super(message);
  }
}

export const tokens = {
  get(): TokenPair | null {
    if (typeof window === "undefined") return null;
    try {
      const raw = window.localStorage.getItem(TOKENS_KEY);
      return raw ? (JSON.parse(raw) as TokenPair) : null;
    } catch {
      return null;
    }
  },
  set(value: TokenPair | null) {
    try {
      if (value) window.localStorage.setItem(TOKENS_KEY, JSON.stringify(value));
      else window.localStorage.removeItem(TOKENS_KEY);
    } catch {
      /* storage unavailable: session stays in memory only */
    }
    window.dispatchEvent(new Event("nomadiq:auth"));
  },
};

let refreshing: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const current = tokens.get();
  if (!current) return false;
  refreshing ??= fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: current.refresh_token }),
  })
    .then(async (res) => {
      if (!res.ok) {
        tokens.set(null);
        return false;
      }
      tokens.set((await res.json()) as TokenPair);
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

type Options = { method?: string; body?: unknown; form?: FormData; auth?: boolean; headers?: Record<string, string>; signal?: AbortSignal };

export async function request<T>(path: string, opts: Options = {}, retried = false): Promise<T> {
  const headers: Record<string, string> = { ...opts.headers };
  const access = tokens.get()?.access_token;
  if (access && opts.auth !== false) headers.Authorization = `Bearer ${access}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { method: opts.method ?? (body ? "POST" : "GET"), headers, body, signal: opts.signal });
  } catch {
    throw new ApiError(0, "network", "Can't reach NomadIQ. Check your connection and that the API is running.");
  }

  if (res.status === 401 && !retried && access && (await refreshTokens())) {
    return request<T>(path, opts, true);
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = (data as ApiErrorBody | null)?.error;
    throw new ApiError(res.status, err?.code ?? "http_error", err?.message ?? `Request failed (${res.status})`, err?.details);
  }
  return data as T;
}

const q = (params: Record<string, string | number | undefined | null>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  const str = s.toString();
  return str ? `?${str}` : "";
};

export const api = {
  // auth
  register: (body: { email: string; password: string; name: string }) => request<AuthResponse>("/auth/register", { body, auth: false }),
  login: (body: { email: string; password: string }) => request<AuthResponse>("/auth/login", { body, auth: false }),
  logout: (refresh_token: string) => request<void>("/auth/logout", { body: { refresh_token }, auth: false }),

  // users
  me: () => request<User>("/users/me"),
  updateMe: (body: { name?: string; preferences?: Partial<UserPreferences> }) => request<User>("/users/me", { method: "PATCH", body }),
  travelers: () => request<Traveler[]>("/users/me/travelers"),
  addTraveler: (body: TravelerInfo & { label: string }) => request<Traveler>("/users/me/travelers", { body }),
  deleteTraveler: (id: string) => request<void>(`/users/me/travelers/${id}`, { method: "DELETE" }),

  // trips
  createTrip: (body: TripInputs & { generate?: boolean }) => request<Trip>("/trips", { body }),
  trips: (page = 1, limit = 20) => request<Page<TripSummary>>(`/trips${q({ page, limit })}`),
  trip: (id: string) => request<Trip>(`/trips/${id}`),
  tripStatus: (id: string) => request<TripProgress>(`/trips/${id}/status`),
  regenerate: (id: string) => request<Trip>(`/trips/${id}/generate`, { method: "POST" }),
  deleteTrip: (id: string) => request<void>(`/trips/${id}`, { method: "DELETE" }),
  tripChat: (id: string, message: string) => request<TripChatResponse>(`/trips/${id}/chat`, { body: { message } }),
  tripChatHistory: (id: string) => request<TripMessage[]>(`/trips/${id}/chat`),
  shareTrip: (id: string) => request<{ share_token: string; share_url: string }>(`/trips/${id}/share`, { method: "POST" }),
  sharedTrip: (token: string) => request<Trip>(`/shared/trips/${token}`, { auth: false }),

  // search
  search: <T extends AnyOffer>(kind: "flights" | "hotels" | "trains" | "buses" | "activities", body: Record<string, unknown>) =>
    request<SearchResponse<T>>(`/search/${kind}`, { body }),
  airports: (query: string) => request<Airport[]>(`/search/airports${q({ q: query })}`),
  offer: (offerId: string) => request<AnyOffer>(`/search/offers/${encodeURIComponent(offerId)}`),

  // bookings
  createBooking: (body: { offer_id: string; traveler_ids?: string[]; travelers?: TravelerInfo[]; contact: { email: string; phone: string }; trip_id?: string }, idempotencyKey: string) =>
    request<Booking>("/bookings", { body, headers: { "Idempotency-Key": idempotencyKey } }),
  confirmBooking: (id: string, expected_total: Money, payment_token?: string) => request<Booking>(`/bookings/${id}/confirm`, { body: { expected_total, payment_token } }),
  cancelBooking: (id: string) => request<Booking>(`/bookings/${id}/cancel`, { method: "POST" }),
  bookings: (page = 1) => request<Page<BookingSummary>>(`/bookings${q({ page, limit: 50 })}`),
  booking: (id: string) => request<Booking>(`/bookings/${id}`),

  // explore (public)
  places: (query: string) => request<Place[]>(`/explore/places${q({ q: query })}`, { auth: false }),
  destination: (query: string) => request<DestinationOverview>(`/explore/destination${q({ q: query })}`, { auth: false }),
  images: (query: string, limit = 1) => request<MediaImage[]>(`/explore/images${q({ q: query, limit })}`, { auth: false }),

  // assistant + voice
  ask: (body: { message: string; conversation_id?: string | null; trip_id?: string | null; selected_offer_id?: string | null }) => request<AssistantReply>("/assistant/messages", { body }),
  conversationMessages: (id: string) => request<AssistantMessage[]>(`/assistant/conversations/${id}/messages`),
  voice: (audio: Blob, fields: { conversation_id?: string | null; selected_offer_id?: string | null }) => {
    const form = new FormData();
    form.append("audio", audio, "voice.webm");
    for (const [k, v] of Object.entries(fields)) if (v) form.append(k, v);
    return request<AssistantReply>("/voice/assistant", { form });
  },
};
