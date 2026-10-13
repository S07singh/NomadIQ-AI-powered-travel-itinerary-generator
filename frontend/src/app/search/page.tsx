"use client";

import clsx from "clsx";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Checkout } from "@/components/checkout";
import { OfferRow } from "@/components/offers";
import { Button, Field, Loading, Notice, Page, PageTitle, SelectField } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { isoDaysFromNow } from "@/lib/format";
import type { AnyOffer } from "@/lib/types";

const TABS = [
  { id: "flights", label: "Flights" },
  { id: "trains", label: "Trains" },
  { id: "buses", label: "Buses" },
  { id: "hotels", label: "Hotels" },
  { id: "activities", label: "Things to do" },
] as const;
type Tab = (typeof TABS)[number]["id"];
type SortKey = "price" | "time";

async function toIata(value: string): Promise<string> {
  const v = value.trim();
  if (/^[A-Za-z]{3}$/.test(v)) return v.toUpperCase();
  const hits = await api.airports(v);
  if (!hits.length) throw new ApiError(422, "unknown_airport", `We couldn't find an airport for "${v}". Try the city name or a 3-letter code.`);
  return hits[0].iata_code;
}

function SearchInner() {
  const user = useRequireUser();
  const params = useSearchParams();
  const router = useRouter();
  const initialTab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "flights") as Tab;
  const [tab, setTab] = useState<Tab>(initialTab);
  const [form, setForm] = useState({
    origin: params.get("origin") ?? "",
    destination: params.get("destination") ?? params.get("city") ?? "",
    date: params.get("date") || params.get("check_in") || isoDaysFromNow(14),
    returnDate: "",
    checkOut: params.get("check_out") || isoDaysFromNow(16),
    adults: params.get("adults") ?? "1",
    travelClass: "",
    currency: params.get("currency") ?? "INR",
  });
  const [results, setResults] = useState<AnyOffer[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("price");

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const run = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    setSelected(null);
    try {
      const adults = Number(form.adults) || 1;
      let res;
      if (tab === "flights") {
        const [origin, destination] = await Promise.all([toIata(form.origin), toIata(form.destination)]);
        res = await api.search("flights", { origin, destination, departure_date: form.date, return_date: form.returnDate || undefined, adults, currency: form.currency });
      } else if (tab === "trains" || tab === "buses") {
        res = await api.search(tab, { origin: form.origin, destination: form.destination, date: form.date, passengers: adults, travel_class: form.travelClass || undefined, currency: form.currency });
      } else if (tab === "hotels") {
        res = await api.search("hotels", { city: form.destination, check_in: form.date, check_out: form.checkOut, adults: Math.max(adults, 1), currency: form.currency });
      } else {
        res = await api.search("activities", { destination: form.destination, date: form.date, currency: form.currency });
      }
      setResults(res.results);
    } catch (err) {
      setResults(null);
      setError(err instanceof ApiError ? (err.code === "validation_error" ? "Check the places and dates. Dates can't be in the past." : err.message) : "Search failed. Try again.");
    } finally {
      setBusy(false);
    }
  };

  // Run automatically when arriving from a trip with the fields filled in.
  useEffect(() => {
    if (user && form.destination && (tab === "hotels" || tab === "activities" || form.origin)) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  if (!user) return <Page><Loading /></Page>;

  const switchTab = (t: Tab) => {
    setTab(t);
    setResults(null);
    setError(null);
    router.replace(`/search?tab=${t}`, { scroll: false });
  };

  const sorted = results
    ? [...results].sort((a, b) => {
        if (sort === "price") return a.price.amount - b.price.amount;
        const time = (o: AnyOffer) => ("departure_at" in o ? o.departure_at : "slices" in o ? o.slices[0].departure_at : "");
        return time(a).localeCompare(time(b));
      })
    : null;
  const needsOrigin = tab === "flights" || tab === "trains" || tab === "buses";

  return (
    <Page>
      <PageTitle sub="Live fares and rooms. Pick one to hold the price, then confirm and pay.">Tickets and stays</PageTitle>
      <div role="tablist" aria-label="What to book" className="flex gap-6 overflow-x-auto border-b border-rule mb-8">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => switchTab(t.id)}
            className={clsx("pb-3 font-bold whitespace-nowrap border-b-4 -mb-px", tab === t.id ? "border-signal" : "border-transparent text-slate hover:text-ink")}
          >
            {t.label}
          </button>
        ))}
      </div>

      <form onSubmit={run} className="grid grid-cols-2 lg:grid-cols-[repeat(6,minmax(0,1fr))_auto] gap-4 items-end">
        {needsOrigin ? <Field label="From" required placeholder={tab === "flights" ? "BLR or Bengaluru" : "New Delhi"} value={form.origin} onChange={set("origin")} /> : null}
        <Field
          label={needsOrigin ? "To" : tab === "hotels" ? "City" : "Place"}
          required
          placeholder={tab === "flights" ? "JAI or Jaipur" : "Jaipur"}
          value={form.destination}
          onChange={set("destination")}
          className={needsOrigin ? "" : "lg:col-span-2"}
        />
        <Field label={tab === "hotels" ? "Check in" : "Date"} type="date" required value={form.date} onChange={set("date")} />
        {tab === "flights" ? <Field label="Return (optional)" type="date" value={form.returnDate} onChange={set("returnDate")} /> : null}
        {tab === "hotels" ? <Field label="Check out" type="date" required value={form.checkOut} onChange={set("checkOut")} /> : null}
        {tab === "trains" ? (
          <SelectField label="Class" value={form.travelClass} onChange={set("travelClass")}>
            <option value="">Any</option>
            {["SL", "3A", "2A", "1A", "CC", "EC"].map((c) => <option key={c}>{c}</option>)}
          </SelectField>
        ) : null}
        {tab === "buses" ? (
          <SelectField label="Seat" value={form.travelClass} onChange={set("travelClass")}>
            <option value="">Any</option>
            <option>AC Sleeper</option>
            <option>AC Seater</option>
          </SelectField>
        ) : null}
        {tab !== "activities" ? <Field label={tab === "hotels" ? "Guests" : "Travelers"} type="number" min={1} max={9} value={form.adults} onChange={set("adults")} /> : null}
        <SelectField label="Currency" value={form.currency} onChange={set("currency")}>
          {["INR", "USD", "EUR", "GBP"].map((c) => <option key={c}>{c}</option>)}
        </SelectField>
        <Button type="submit" disabled={busy} className="col-span-2 lg:col-span-1">{busy ? "Searching" : "Search"}</Button>
      </form>

      <div className="mt-10">
        {error ? <Notice>{error}</Notice> : null}
        {busy ? <Loading label="Checking live prices" /> : null}
        {sorted && !busy ? (
          sorted.length === 0 ? (
            <p className="text-slate text-lg">Nothing available for those dates. Try a day either side.</p>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <p className="text-slate">{sorted.length} options</p>
                {tab !== "hotels" && tab !== "activities" ? (
                  <div className="flex gap-4 text-sm font-bold" role="group" aria-label="Sort">
                    {(["price", "time"] as SortKey[]).map((k) => (
                      <button key={k} aria-pressed={sort === k} onClick={() => setSort(k)} className={sort === k ? "underline decoration-signal decoration-[3px] underline-offset-4" : "text-slate"}>
                        {k === "price" ? "Cheapest" : "Earliest"}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <ul className="divide-y divide-rule border-y border-rule">
                {sorted.map((offer) => (
                  <li key={offer.offer_id} className={clsx("py-6", selected === offer.offer_id && "bg-sheet -mx-4 px-4 sm:-mx-6 sm:px-6")}>
                    <OfferRow
                      offer={offer}
                      action={selected === offer.offer_id ? null : <Button variant="quiet" onClick={() => setSelected(offer.offer_id)}>Select</Button>}
                    />
                    {selected === offer.offer_id ? <Checkout offer={offer} onClose={() => setSelected(null)} /> : null}
                  </li>
                ))}
              </ul>
            </>
          )
        ) : null}
      </div>
    </Page>
  );
}

export default function SearchPage() {
  return (
    <Suspense>
      <SearchInner />
    </Suspense>
  );
}
