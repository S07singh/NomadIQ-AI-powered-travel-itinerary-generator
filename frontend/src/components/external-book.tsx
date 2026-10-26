import { ExternalLink as ExternalIcon } from "lucide-react";
import type { AnyOffer } from "@/lib/types";

const SITE_NAMES: Record<string, string> = { google_flights: "Google Flights" };

export function siteName(provider: string): string {
  return SITE_NAMES[provider] ?? "the provider's site";
}

export function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** For fares we can show but not sell (e.g. Google Flights prices): book on the source site. */
export function ExternalBook({ offer }: { offer: AnyOffer }) {
  if (!offer.deep_link) return null;
  return (
    <a
      href={offer.deep_link}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center justify-center gap-2 rounded-md px-4 h-11 font-bold text-[0.95rem] border-2 border-ink/80 text-ink hover:bg-ink hover:text-white whitespace-nowrap"
    >
      Book on {siteName(offer.provider)} <ExternalIcon size={15} aria-hidden />
    </a>
  );
}
