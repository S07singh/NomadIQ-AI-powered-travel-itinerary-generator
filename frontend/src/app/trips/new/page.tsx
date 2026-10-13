"use client";

import clsx from "clsx";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button, Field, Loading, Notice, Page, PageTitle, SelectField } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import type { TravelStyle, TripPace } from "@/lib/types";

const VIBES = ["culture", "food", "nature", "adventure", "relaxation", "nightlife", "shopping", "spiritual", "romance", "family", "photography"];
const STYLES: { value: TravelStyle; label: string; note: string }[] = [
  { value: "backpacker", label: "Backpacker", note: "Hostels, buses, street food" },
  { value: "budget", label: "Budget", note: "Simple stays, good value" },
  { value: "comfort", label: "Comfort", note: "Good hotels, some taxis" },
  { value: "luxury", label: "Luxury", note: "The best of everything" },
];
const PACES: { value: TripPace; label: string }[] = [
  { value: "relaxed", label: "Relaxed, 2 to 3 things a day" },
  { value: "moderate", label: "Steady, 3 to 4 things a day" },
  { value: "packed", label: "Packed, see as much as possible" },
];

function NewTrip() {
  const user = useRequireUser();
  const router = useRouter();
  const params = useSearchParams();
  const [destination, setDestination] = useState(params.get("to") ?? "");
  const [origin, setOrigin] = useState(params.get("from") ?? "");
  const [start, setStart] = useState(params.get("start") ?? "");
  const [days, setDays] = useState(params.get("days") ?? "4");
  const [adults, setAdults] = useState("2");
  const [children, setChildren] = useState("0");
  const [budget, setBudget] = useState(params.get("budget") ?? "");
  const [currency, setCurrency] = useState(params.get("currency") ?? "INR");
  const [style, setStyle] = useState<TravelStyle>("comfort");
  const [pace, setPace] = useState<TripPace>("moderate");
  const [vibes, setVibes] = useState<string[]>(["culture", "food"]);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!user) return <Page><Loading /></Page>;

  const toggleVibe = (v: string) => setVibes((cur) => (cur.includes(v) ? cur.filter((x) => x !== v) : cur.length >= 8 ? cur : [...cur, v]));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const trip = await api.createTrip({
        destination,
        origin: origin || null,
        start_date: start || null,
        duration_days: Number(days) || 3,
        travelers: { adults: Number(adults) || 1, children: Number(children) || 0, infants: 0 },
        budget: budget ? { amount: Number(budget), currency, flexible: false } : null,
        travel_style: style,
        pace,
        vibes,
        additional_info: notes,
        generate: true,
      });
      router.push(`/trips/${trip.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't start planning. Try again.");
      setBusy(false);
    }
  };

  return (
    <Page className="pb-10">
      <PageTitle sub="The more you tell us, the less you'll change later. Everything here can be edited once the route is drawn.">New trip</PageTitle>
      <form onSubmit={submit} className="grid lg:grid-cols-[1fr_320px] gap-12">
        <div className="space-y-10">
          <fieldset className="grid sm:grid-cols-2 gap-5">
            <legend className="heading text-xl mb-4">Where and when</legend>
            <Field label="Destination" required placeholder="Jaipur, India" value={destination} onChange={(e) => setDestination(e.target.value)} />
            <Field label="Starting from" placeholder="Bengaluru" value={origin} onChange={(e) => setOrigin(e.target.value)} />
            <Field label="First day" type="date" value={start} onChange={(e) => setStart(e.target.value)} hint="Leave empty if your dates are open." />
            <Field label="Number of days" type="number" min={1} max={30} required value={days} onChange={(e) => setDays(e.target.value)} />
          </fieldset>

          <fieldset className="grid grid-cols-2 sm:grid-cols-4 gap-5">
            <legend className="heading text-xl mb-4">Who and how much</legend>
            <Field label="Adults" type="number" min={1} max={20} value={adults} onChange={(e) => setAdults(e.target.value)} />
            <Field label="Children" type="number" min={0} max={10} value={children} onChange={(e) => setChildren(e.target.value)} />
            <Field label="Budget for everyone" inputMode="numeric" placeholder="40000" value={budget} onChange={(e) => setBudget(e.target.value.replace(/[^\d]/g, ""))} />
            <SelectField label="Currency" value={currency} onChange={(e) => setCurrency(e.target.value)}>
              {["INR", "USD", "EUR", "GBP", "AED", "SGD"].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </SelectField>
          </fieldset>

          <fieldset>
            <legend className="heading text-xl mb-4">How you like to travel</legend>
            <div className="grid sm:grid-cols-4 gap-3" role="radiogroup">
              {STYLES.map((s) => (
                <label key={s.value} className={clsx("cursor-pointer rounded-md border-2 px-4 py-3", style === s.value ? "border-ink bg-signal/25" : "border-rule bg-sheet hover:border-ink/50")}>
                  <input type="radio" name="style" value={s.value} checked={style === s.value} onChange={() => setStyle(s.value)} className="sr-only" />
                  <span className="block font-extrabold">{s.label}</span>
                  <span className="block text-sm text-slate">{s.note}</span>
                </label>
              ))}
            </div>
            <div className="mt-6 max-w-sm">
              <SelectField label="Pace" value={pace} onChange={(e) => setPace(e.target.value as TripPace)}>
                {PACES.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </SelectField>
            </div>
          </fieldset>

          <fieldset>
            <legend className="heading text-xl mb-1">What you&apos;re into</legend>
            <p className="text-slate mb-4">Pick up to eight.</p>
            <div className="flex flex-wrap gap-2">
              {VIBES.map((v) => {
                const on = vibes.includes(v);
                return (
                  <button
                    type="button"
                    key={v}
                    aria-pressed={on}
                    onClick={() => toggleVibe(v)}
                    className={clsx("h-10 px-4 rounded-full border-2 font-semibold capitalize", on ? "border-ink bg-ink text-white" : "border-rule bg-sheet text-ink hover:border-ink/50")}
                  >
                    {v}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <label className="block">
            <span className="heading text-xl block mb-1">Anything else</span>
            <span className="block text-slate mb-3">Dietary needs, a birthday dinner, a bad knee, things you&apos;ve already seen.</span>
            <textarea
              rows={4}
              maxLength={2000}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-md border-2 border-rule bg-sheet p-3 focus:outline-none focus:border-platform"
            />
          </label>
        </div>

        <aside className="lg:sticky lg:top-24 self-start border-l-4 border-signal pl-6">
          <p className="heading text-2xl">{destination || "Your destination"}</p>
          <p className="text-slate mt-1">
            {days || "?"} days{origin ? ` from ${origin}` : ""}
            {budget ? `, about ${Number(budget).toLocaleString("en-IN")} ${currency}` : ""}
          </p>
          {error ? <div className="mt-5"><Notice>{error}</Notice></div> : null}
          <Button type="submit" disabled={busy || !destination.trim()} className="mt-6 w-full">
            {busy ? "Starting" : "Draw my route"}
          </Button>
          <p className="mt-3 text-sm text-slate">Planning runs in the background. You can leave the page and come back.</p>
        </aside>
      </form>
    </Page>
  );
}

export default function NewTripPage() {
  return (
    <Suspense>
      <NewTrip />
    </Suspense>
  );
}
