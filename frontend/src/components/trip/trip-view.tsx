"use client";

import clsx from "clsx";
import { Play } from "lucide-react";
import { useState } from "react";
import { dateRange } from "@/lib/format";
import type { Trip } from "@/lib/types";
import { Photo } from "../photo";
import { RouteItinerary } from "./route-itinerary";
import { Budget, Food, GoodToKnow, Sights, Stays } from "./trip-sections";

const TABS = [
  { id: "route", label: "Route" },
  { id: "sights", label: "Sights" },
  { id: "stays", label: "Stays" },
  { id: "food", label: "Food" },
  { id: "budget", label: "Budget" },
  { id: "info", label: "Good to know" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export function TripHeading({ trip, actions }: { trip: Trip; actions?: React.ReactNode }) {
  const people = trip.travelers.adults + trip.travelers.children;
  return (
    <div className="pt-10 pb-6 flex flex-wrap items-end justify-between gap-6">
      <div>
        <h1 className="display text-4xl sm:text-6xl max-w-[18ch]">{trip.destination.split(",")[0]}</h1>
        <p className="mt-3 text-lg text-slate">
          {dateRange(trip.start_date, trip.end_date, trip.duration_days)}, {trip.duration_days} days, {people} {people === 1 ? "traveler" : "travelers"}
          {trip.origin ? `, from ${trip.origin}` : ""}
        </p>
      </div>
      {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
    </div>
  );
}

export function TripView({ trip, aside }: { trip: Trip; aside?: React.ReactNode }) {
  const [tab, setTab] = useState<Tab>("route");
  const plan = trip.plan;
  if (!plan) return null;
  const currency = trip.budget?.currency ?? "USD";
  const gallery = plan.gallery.length ? plan.gallery : plan.cover_image ? [plan.cover_image] : [];

  return (
    <>
      {gallery.length ? (
        <div className="grid grid-cols-4 grid-rows-2 gap-1.5 h-[260px] sm:h-[380px] rounded-md overflow-hidden">
          <Photo image={gallery[0]} className="col-span-4 sm:col-span-2 row-span-2" credit />
          {gallery.slice(1, 5).map((img) => (
            <Photo key={img.url} image={img} thumb className="hidden sm:block" />
          ))}
        </div>
      ) : null}

      {plan.summary ? <p className="mt-8 text-xl max-w-[62ch] leading-relaxed">{plan.summary}</p> : null}

      <div className="mt-10 grid lg:grid-cols-[1fr_340px] gap-12">
        <div className="min-w-0">
          <div role="tablist" aria-label="Trip sections" className="flex gap-6 overflow-x-auto border-b border-rule mb-10 -mx-1 px-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                aria-controls={`panel-${t.id}`}
                id={`tab-${t.id}`}
                onClick={() => setTab(t.id)}
                className={clsx("pb-3 font-bold whitespace-nowrap border-b-4 -mb-px", tab === t.id ? "border-signal text-ink" : "border-transparent text-slate hover:text-ink")}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
            {tab === "route" && <RouteItinerary days={plan.days} currency={currency} />}
            {tab === "sights" && <Sights plan={plan} />}
            {tab === "stays" && <Stays plan={plan} currency={currency} />}
            {tab === "food" && <Food plan={plan} currency={currency} />}
            {tab === "budget" && <Budget plan={plan} />}
            {tab === "info" && <GoodToKnow plan={plan} trip={trip} />}
          </div>
        </div>

        <aside className="space-y-10 lg:sticky lg:top-24 self-start">
          {aside}
          {plan.videos.length ? (
            <div>
              <h2 className="heading text-lg mb-3">Watch before you go</h2>
              <ul className="space-y-2">
                {plan.videos.map((v) => (
                  <li key={v.url}>
                    <a href={v.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 font-semibold text-platform hover:underline underline-offset-4">
                      <Play size={16} aria-hidden /> {v.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {plan.highlights.length ? (
            <div>
              <h2 className="heading text-lg mb-3">Highlights</h2>
              <ul className="space-y-1.5 text-slate list-disc pl-5">{plan.highlights.map((h) => <li key={h}>{h}</li>)}</ul>
            </div>
          ) : null}
        </aside>
      </div>
    </>
  );
}
