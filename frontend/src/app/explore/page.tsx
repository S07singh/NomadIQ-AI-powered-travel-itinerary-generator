"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Page, PageTitle } from "@/components/ui";
import { api } from "@/lib/api";
import type { Place } from "@/lib/types";

export default function ExplorePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [places, setPlaces] = useState<Place[]>([]);

  useEffect(() => {
    if (query.trim().length < 2) return;
    const t = setTimeout(() => api.places(query).then(setPlaces).catch(() => setPlaces([])), 220);
    return () => clearTimeout(t);
  }, [query]);

  const suggestions = query.trim().length >= 2 ? places : [];
  const go = (name: string) => router.push(`/explore/${encodeURIComponent(name)}`);

  return (
    <Page>
      <PageTitle sub="Photos, a short guide, the week's weather and videos for any city, town or region.">Look before you go</PageTitle>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim()) go(query.trim());
        }}
        className="max-w-[640px]"
      >
        <label htmlFor="explore-q" className="sr-only">Place</label>
        <div className="flex gap-3">
          <input
            id="explore-q"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Udaipur, Kyoto, Lisbon"
            autoComplete="off"
            className="flex-1 min-w-0 h-14 text-xl font-semibold rounded-md border-2 border-ink bg-sheet px-4 focus:outline-none focus:border-platform"
          />
          <Button type="submit" className="h-14 px-6">Show me</Button>
        </div>
        {suggestions.length ? (
          <ul className="mt-2 border-2 border-rule rounded-md bg-sheet divide-y divide-rule" aria-label="Matching places">
            {suggestions.map((p) => (
              <li key={`${p.name}-${p.lat}`}>
                <button type="button" onClick={() => go(`${p.name}${p.country ? `, ${p.country}` : ""}`)} className="w-full text-left px-4 py-3 hover:bg-paper">
                  <span className="font-bold">{p.name}</span>
                  <span className="text-slate">{[p.region, p.country].filter(Boolean).map((x) => `, ${x}`).join("")}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </form>
    </Page>
  );
}
