import Link from "next/link";
import { ExternalLink, MapPin, Play } from "lucide-react";
import { currencySymbol, money } from "@/lib/format";
import type { Trip, TripPlan } from "@/lib/types";
import { Photo } from "../photo";

const LINE_LABELS = { accommodation: "Stays", food: "Food", activities: "Things to do", local_transport: "Getting around", misc: "Buffer" } as const;

export function Stays({ plan, currency }: { plan: TripPlan; currency: string }) {
  if (!plan.hotels.length) return <p className="text-slate">No stays suggested. Search live hotel prices instead.</p>;
  return (
    <ul className="divide-y divide-rule border-y border-rule">
      {plan.hotels.map((h) => {
        const hint = h.search_hint as Record<string, string | number> | undefined;
        const searchHref = hint ? `/search?tab=hotels&${new URLSearchParams(Object.entries(hint).map(([k, v]) => [k, String(v)]))}` : "/search?tab=hotels";
        return (
          <li key={h.name} className="py-6 grid sm:grid-cols-[1fr_auto] gap-4">
            <div>
              <h3 className="heading text-xl">{h.name}</h3>
              <p className="text-slate">
                {[h.area, h.rating ? `${h.rating.toFixed(1)} rating` : null].filter(Boolean).join(", ")}
              </p>
              {h.why ? <p className="mt-2 max-w-[60ch]">{h.why}</p> : null}
              {h.amenities.length ? <p className="mt-1 text-sm text-slate">{h.amenities.join(", ")}</p> : null}
              <div className="mt-3 flex gap-5 text-sm font-bold">
                <Link href={searchHref} className="text-platform hover:underline underline-offset-4">Check live prices</Link>
                {h.maps_url ? (
                  <a href={h.maps_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-platform hover:underline underline-offset-4">
                    <MapPin size={14} aria-hidden /> Map
                  </a>
                ) : null}
              </div>
            </div>
            {h.price_per_night ? (
              <p className="sm:text-right">
                <span className="heading text-2xl tabular">{money(h.price_per_night, currency)}</span>
                <span className="block text-sm text-slate">a night, estimated</span>
              </p>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

export function Food({ plan, currency }: { plan: TripPlan; currency: string }) {
  return (
    <div className="space-y-10">
      {plan.local_dishes.length ? (
        <div>
          <h3 className="heading text-xl mb-3">Eat while you&apos;re there</h3>
          <p className="text-lg max-w-[60ch]">{plan.local_dishes.join(", ")}.</p>
        </div>
      ) : null}
      <ul className="grid sm:grid-cols-2 gap-x-10 gap-y-8">
        {plan.restaurants.map((r) => (
          <li key={r.name} className="border-t-2 border-ink pt-4">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="heading text-lg">{r.name}</h3>
              {r.price_level ? <span className="tabular font-bold text-slate" aria-label={`Price level ${r.price_level} of 4`}>{currencySymbol(currency).repeat(r.price_level)}</span> : null}
            </div>
            <p className="text-slate">{[r.cuisine, r.area].filter(Boolean).join(", ")}</p>
            {r.must_try.length ? <p className="mt-2">Order: {r.must_try.join(", ")}</p> : null}
            {r.avg_cost_per_person ? <p className="text-sm text-slate tabular">About {money(r.avg_cost_per_person, currency)} a person</p> : null}
            {r.maps_url ? (
              <a href={r.maps_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm font-bold text-platform hover:underline underline-offset-4">
                <MapPin size={14} aria-hidden /> Map
              </a>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Budget({ plan }: { plan: TripPlan }) {
  const b = plan.budget;
  if (!b) return <p className="text-slate">No budget yet.</p>;
  const max = Math.max(...b.lines.map((l) => l.amount), 1);
  return (
    <div className="max-w-[720px]">
      <div className="flex flex-wrap items-end gap-x-10 gap-y-3">
        <p>
          <span className="block text-slate font-semibold">Estimated total</span>
          <span className="display text-5xl tabular">{money(b.total, b.currency)}</span>
        </p>
        <p className="text-slate tabular pb-1.5">
          {money(b.per_person, b.currency)} a person, {money(b.per_day, b.currency)} a day
        </p>
      </div>
      {b.budget_limit ? (
        <p className={`mt-4 font-bold ${b.within_budget ? "text-platform-deep" : "text-brick"}`}>
          {b.within_budget ? `Within your ${money(b.budget_limit, b.currency)} budget.` : `Over your ${money(b.budget_limit, b.currency)} budget.`}
        </p>
      ) : null}
      <table className="mt-8 w-full tabular">
        <caption className="sr-only">Budget by category</caption>
        <tbody>
          {b.lines.map((line) => (
            <tr key={line.category} className="border-t border-rule align-top">
              <th scope="row" className="text-left font-bold py-3 pr-4 w-40">{LINE_LABELS[line.category]}</th>
              <td className="py-3 pr-4">
                <span className="block h-2.5 rounded-full bg-ink/85 mt-2" style={{ width: `${Math.max((line.amount / max) * 100, 2)}%` }} aria-hidden />
                <span className="block text-sm text-slate mt-1.5">{line.note}</span>
              </td>
              <td className="py-3 text-right font-bold whitespace-nowrap">{money(line.amount, b.currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {b.tips.length ? (
        <ul className="mt-8 space-y-2 list-disc pl-5 text-slate">
          {b.tips.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function GoodToKnow({ plan, trip }: { plan: TripPlan; trip: Trip }) {
  const info = plan.local_info;
  const facts = info
    ? ([
        ["Language", info.language],
        ["Money", info.currency],
        ["Time zone", info.timezone],
        ["Best season", info.best_time_to_visit],
        ["Getting around", info.getting_around],
        ["Emergency", info.emergency_numbers.join(", ")],
      ] as const).filter(([, v]) => v)
    : [];
  return (
    <div className="grid lg:grid-cols-2 gap-12">
      <div>
        {facts.length ? (
          <dl className="divide-y divide-rule border-y border-rule">
            {facts.map(([k, v]) => (
              <div key={k} className="grid grid-cols-[9rem_1fr] gap-4 py-3">
                <dt className="font-bold">{k}</dt>
                <dd className="text-slate">{v}</dd>
              </div>
            ))}
          </dl>
        ) : null}
        {plan.travel_tips.length ? (
          <>
            <h3 className="heading text-xl mt-10 mb-3">Tips</h3>
            <ul className="space-y-2 list-disc pl-5">{plan.travel_tips.map((t) => <li key={t}>{t}</li>)}</ul>
          </>
        ) : null}
      </div>
      <div>
        {plan.packing_list.length ? (
          <>
            <h3 className="heading text-xl mb-3">Pack</h3>
            <ul className="space-y-2">
              {plan.packing_list.map((p) => (
                <li key={p}>
                  <label className="flex items-center gap-3">
                    <input type="checkbox" className="w-5 h-5 accent-platform" /> {p}
                  </label>
                </li>
              ))}
            </ul>
          </>
        ) : null}
        <h3 className="heading text-xl mt-10 mb-3">Getting there</h3>
        <p className="text-slate max-w-[50ch]">Compare live fares from {trip.origin || "your city"} to {trip.destination.split(",")[0]}.</p>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 font-bold">
          {(["flights", "trains", "buses"] as const).map((tab) => (
            <Link
              key={tab}
              href={`/search?tab=${tab}&${new URLSearchParams({ origin: trip.origin ?? "", destination: trip.destination.split(",")[0], date: trip.start_date ?? "" })}`}
              className="text-platform hover:underline underline-offset-4 capitalize"
            >
              {tab}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

export function Sights({ plan }: { plan: TripPlan }) {
  return (
    <ul className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-10">
      {plan.attractions.map((a) => (
        <li key={a.name}>
          <Photo image={a.images[0]} alt={a.name} className="aspect-[4/3] rounded-sm" credit />
          <h3 className="heading text-lg mt-3">{a.name}</h3>
          <p className="text-slate text-[0.95rem]">{a.description}</p>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm font-bold">
            {a.maps_url ? (
              <a href={a.maps_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-platform hover:underline underline-offset-4">
                <MapPin size={14} aria-hidden /> Map
              </a>
            ) : null}
            {a.videos[0] ? (
              <a href={a.videos[0].url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-platform hover:underline underline-offset-4">
                <Play size={14} aria-hidden /> Videos
              </a>
            ) : null}
            {a.images[0]?.source_url ? (
              <a href={a.images[0].source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-slate hover:underline underline-offset-4">
                <ExternalLink size={14} aria-hidden /> About
              </a>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}
