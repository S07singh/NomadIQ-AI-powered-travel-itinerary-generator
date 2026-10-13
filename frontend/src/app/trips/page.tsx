"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Photo } from "@/components/photo";
import { ButtonLink, Loading, Notice, Page, PageTitle } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { dateRange } from "@/lib/format";
import type { TripStatus, TripSummary } from "@/lib/types";

const STATUS: Record<TripStatus, string> = { draft: "Not planned", queued: "Planning", generating: "Planning", ready: "", failed: "Needs another try" };

export default function TripsPage() {
  const user = useRequireUser();
  const [trips, setTrips] = useState<TripSummary[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (user) api.trips(1, 50).then((p) => setTrips(p.items)).catch(() => setError(true));
  }, [user]);

  return (
    <Page>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle>My trips</PageTitle>
        <ButtonLink href="/trips/new" className="mb-8">New trip</ButtonLink>
      </div>
      {error ? <Notice>Couldn&apos;t load your trips. Refresh to try again.</Notice> : null}
      {!trips && !error ? <Loading /> : null}
      {trips?.length === 0 ? (
        <div className="border-l-4 border-signal pl-6 py-2 max-w-[52ch]">
          <p className="heading text-2xl">No trips yet</p>
          <p className="text-slate mt-2">Start with a destination and a number of days. You&apos;ll get a route you can change by talking to it.</p>
          <ButtonLink href="/trips/new" className="mt-5">Plan your first trip</ButtonLink>
        </div>
      ) : null}
      {trips?.length ? (
        <ul className="divide-y divide-rule border-y border-rule">
          {trips.map((t) => (
            <li key={t.id}>
              <Link href={`/trips/${t.id}`} className="grid grid-cols-[88px_1fr] sm:grid-cols-[140px_1fr_auto] gap-5 py-5 items-center group">
                <Photo image={t.cover_image} thumb className="aspect-[4/3] rounded-sm" alt={t.destination} />
                <div className="min-w-0">
                  <h2 className="heading text-xl sm:text-2xl group-hover:underline underline-offset-4 decoration-signal decoration-[3px]">{t.destination.split(",")[0]}</h2>
                  <p className="text-slate">{dateRange(t.start_date, t.end_date, t.duration_days)}, {t.duration_days} days, {t.travel_style}</p>
                </div>
                {STATUS[t.status] ? (
                  <span className={`col-start-2 sm:col-start-auto font-bold ${t.status === "failed" ? "text-brick" : "text-slate"}`}>{STATUS[t.status]}</span>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </Page>
  );
}
