import type { Money, WeatherCondition } from "@/api/types";

const SYMBOLS: Record<string, string> = { INR: "₹", USD: "$", EUR: "€", GBP: "£", JPY: "¥" };

export function currencySymbol(currency: string): string {
  return SYMBOLS[currency] ?? currency;
}

export function money(value: Money | number | null | undefined, currency = "USD"): string {
  if (value === null || value === undefined) return "";
  const amount = typeof value === "number" ? value : value.amount;
  const cur = typeof value === "number" ? currency : value.currency;
  const locale = cur === "INR" ? "en-IN" : "en-US";
  const decimals = cur === "INR" || cur === "JPY" || amount >= 1000 ? 0 : 2;
  const formatted = new Intl.NumberFormat(locale, { maximumFractionDigits: decimals }).format(amount);
  return SYMBOLS[cur] ? `${SYMBOLS[cur]}${formatted}` : `${formatted} ${cur}`;
}

export function shortDate(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function weekday(iso?: string | null): string {
  if (!iso) return "";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { weekday: "short" });
}

/** Wall-clock HH:MM as the provider reported it (departures are shown in local station time). */
export function clock(iso: string): string {
  return iso.slice(11, 16);
}

export function duration(minutes?: number | null): string {
  if (!minutes) return "";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h}h ${m ? `${m}m` : ""}`.trim() : `${m}m`;
}

export function dateRange(start?: string | null, end?: string | null, days?: number): string {
  if (start && end) return start === end ? shortDate(start) : `${shortDate(start)} to ${shortDate(end)}`;
  return days ? `${days} days, dates open` : "Dates open";
}

export const WEATHER_WORDS: Record<WeatherCondition, string> = {
  clear: "Clear",
  partly_cloudy: "Some cloud",
  cloudy: "Cloudy",
  fog: "Fog",
  drizzle: "Drizzle",
  rain: "Rain",
  snow: "Snow",
  storm: "Storms",
  unknown: "",
};

export function isoDaysFromNow(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
}
