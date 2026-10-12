// NomadIQ API v1 client for the mobile app. Same endpoints as the website; tokens live in the
// device keychain (expo-secure-store). A 401 triggers one shared refresh-token rotation.

import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import type {
  AnyOffer,
  ApiErrorBody,
  AssistantReply,
  AuthResponse,
  Booking,
  BookingSummary,
  DestinationOverview,
  MediaImage,
  Money,
  Page,
  SearchResponse,
  TokenPair,
  Traveler,
  TravelerInfo,
  Trip,
  TripChatResponse,
  TripInputs,
  TripProgress,
  TripSummary,
  User,
  UserPreferences,
  Airport,
} from "./types";

// Android emulators reach the host machine at 10.0.2.2. On a real phone set EXPO_PUBLIC_API_URL to your LAN IP.
const DEFAULT_HOST = Platform.OS === "android" ? "http://10.0.2.2:8000" : "http://localhost:8000";
export const API_URL = `${process.env.EXPO_PUBLIC_API_URL ?? DEFAULT_HOST}/api/v1`;
const TOKENS_KEY = "nomadiq.tokens";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown) {
    super(message);
  }
}

// SecureStore has no web implementation; the web preview build keeps tokens in localStorage.
const storage = {
  get: (key: string) => (Platform.OS === "web" ? Promise.resolve(globalThis.localStorage?.getItem(key) ?? null) : SecureStore.getItemAsync(key)),
  set: (key: string, value: string) => (Platform.OS === "web" ? Promise.resolve(globalThis.localStorage?.setItem(key, value)) : SecureStore.setItemAsync(key, value)),
  remove: (key: string) => (Platform.OS === "web" ? Promise.resolve(globalThis.localStorage?.removeItem(key)) : SecureStore.deleteItemAsync(key)),
};

let cached: TokenPair | null | undefined;
const listeners = new Set<(signedIn: boolean) => void>();

export const tokens = {
  async get(): Promise<TokenPair | null> {
    if (cached !== undefined) return cached;
    const raw = await storage.get(TOKENS_KEY);
    cached = raw ? (JSON.parse(raw) as TokenPair) : null;
    return cached;
  },
  async set(value: TokenPair | null) {
    cached = value;
    if (value) await storage.set(TOKENS_KEY, JSON.stringify(value));
    else await storage.remove(TOKENS_KEY);
    listeners.forEach((fn) => fn(!!value));
  },
  subscribe(fn: (signedIn: boolean) => void): () => void {
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  },
};

let refreshing: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const current = await tokens.get();
  if (!current) return false;
  refreshing ??= fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: current.refresh_token }),
  })
    .then(async (res) => {
      if (!res.ok) {
        await tokens.set(null);
        return false;
      }
      await tokens.set((await res.json()) as TokenPair);
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

type Options = { method?: string; body?: unknown; form?: FormData; auth?: boolean; headers?: Record<string, string> };

export async function request<T>(path: string, opts: Options = {}, retried = false): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", ...opts.headers };
  const access = opts.auth === false ? null : (await tokens.get())?.access_token;
  if (access) headers.Authorization = `Bearer ${access}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { method: opts.method ?? (body ? "POST" : "GET"), headers, body });
  } catch {
    throw new ApiError(0, "network", "No connection to NomadIQ. Check your internet and try again.");
  }
  if (res.status === 401 && !retried && access && (await refreshTokens())) return request<T>(path, opts, true);
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = (data as ApiErrorBody | null)?.error;
    throw new ApiError(res.status, err?.code ?? "http_error", err?.message ?? `Request failed (${res.status})`, err?.details);
  }
  return data as T;
}

const q = (params: Record<string, string | number | undefined | null>) => {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join("&")}` : "";
};

export const api = {
  register: (body: { email: string; password: string; name: string }) => request<AuthResponse>("/auth/register", { body, auth: false }),
  login: (body: { email: string; password: string }) => request<AuthResponse>("/auth/login", { body, auth: false }),
  logout: (refresh_token: string) => request<void>("/auth/logout", { body: { refresh_token }, auth: false }),

  me: () => request<User>("/users/me"),
  updateMe: (body: { name?: string; preferences?: Partial<UserPreferences> }) => request<User>("/users/me", { method: "PATCH", body }),
  travelers: () => request<Traveler[]>("/users/me/travelers"),
  addTraveler: (body: TravelerInfo & { label: string }) => request<Traveler>("/users/me/travelers", { body }),
  deleteTraveler: (id: string) => request<void>(`/users/me/travelers/${id}`, { method: "DELETE" }),
  registerDevice: (token: string, platform: "ios" | "android") => request("/users/me/devices", { body: { token, platform } }),

  createTrip: (body: TripInputs & { generate?: boolean }) => request<Trip>("/trips", { body }),
  trips: () => request<Page<TripSummary>>(`/trips${q({ page: 1, limit: 50 })}`),
  trip: (id: string) => request<Trip>(`/trips/${id}`),
  tripStatus: (id: string) => request<TripProgress>(`/trips/${id}/status`),
  regenerate: (id: string) => request<Trip>(`/trips/${id}/generate`, { method: "POST" }),
  deleteTrip: (id: string) => request<void>(`/trips/${id}`, { method: "DELETE" }),
  tripChat: (id: string, message: string) => request<TripChatResponse>(`/trips/${id}/chat`, { body: { message } }),
  shareTrip: (id: string) => request<{ share_token: string; share_url: string }>(`/trips/${id}/share`, { method: "POST" }),

  search: <T extends AnyOffer>(kind: "flights" | "hotels" | "trains" | "buses" | "activities", body: Record<string, unknown>) =>
    request<SearchResponse<T>>(`/search/${kind}`, { body }),
  airports: (query: string) => request<Airport[]>(`/search/airports${q({ q: query })}`),

  createBooking: (body: { offer_id: string; traveler_ids: string[]; contact: { email: string; phone: string } }, idempotencyKey: string) =>
    request<Booking>("/bookings", { body, headers: { "Idempotency-Key": idempotencyKey } }),
  confirmBooking: (id: string, expected_total: Money, payment_token?: string) => request<Booking>(`/bookings/${id}/confirm`, { body: { expected_total, payment_token } }),
  cancelBooking: (id: string) => request<Booking>(`/bookings/${id}/cancel`, { method: "POST" }),
  bookings: () => request<Page<BookingSummary>>(`/bookings${q({ page: 1, limit: 50 })}`),
  booking: (id: string) => request<Booking>(`/bookings/${id}`),

  destination: (query: string) => request<DestinationOverview>(`/explore/destination${q({ q: query })}`, { auth: false }),
  images: (query: string, limit = 1) => request<MediaImage[]>(`/explore/images${q({ q: query, limit })}`, { auth: false }),

  ask: (body: { message: string; conversation_id?: string | null; selected_offer_id?: string | null }) => request<AssistantReply>("/assistant/messages", { body }),
  /** Upload a recorded clip (file URI from expo-audio) to the voice assistant. */
  voice: (uri: string, fields: { conversation_id?: string | null; selected_offer_id?: string | null }) => {
    const form = new FormData();
    const ext = uri.split(".").pop()?.toLowerCase() ?? "m4a";
    // React Native's FormData accepts {uri, name, type} file descriptors.
    form.append("audio", { uri, name: `voice.${ext}`, type: ext === "m4a" ? "audio/mp4" : `audio/${ext}` } as unknown as Blob);
    for (const [k, v] of Object.entries(fields)) if (v) form.append(k, v);
    return request<AssistantReply>("/voice/assistant", { form });
  },
};
