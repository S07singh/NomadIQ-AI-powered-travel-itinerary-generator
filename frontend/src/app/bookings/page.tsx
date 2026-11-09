"use client";

import { BedDouble, Bus, Compass, Plane, TrainFront } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ButtonLink, Loading, Notice, Page, PageTitle } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { money, shortDate } from "@/lib/format";
import type { BookingStatus, BookingSummary, OfferKind } from "@/lib/types";

const STATUS: Record<BookingStatus, { label: string; tone: string }> = {
  awaiting_confirmation: { label: "Waiting for payment", tone: "bg-signal/25 text-ink" },
  processing: { label: "Confirming", tone: "bg-rule text-slate" },
  confirmed: { label: "Confirmed", tone: "bg-platform/15 text-platform-deep" },
  failed: { label: "Failed, refunded", tone: "bg-brick/10 text-brick" },
  cancelled: { label: "Cancelled", tone: "bg-rule text-slate" },
  expired: { label: "Hold expired", tone: "bg-rule text-slate" },
};

const KIND_ICON: Record<OfferKind, typeof Plane> = { flight: Plane, train: TrainFront, bus: Bus, hotel: BedDouble, activity: Compass };

export default function BookingsPage() {
  const user = useRequireUser();
  const [items, setItems] = useState<BookingSummary[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (user) api.bookings().then((p) => setItems(p.items)).catch(() => setError(true));
  }, [user]);

  return (
    <Page>
      <PageTitle>Bookings</PageTitle>
      {error ? <Notice>Couldn&apos;t load bookings. Refresh to try again.</Notice> : null}
      {!items && !error ? <Loading /> : null}
      {items?.length === 0 ? (
        <div className="border-l-4 border-signal pl-6 py-2 max-w-[52ch]">
          <p className="heading text-2xl">Nothing booked yet</p>
          <p className="text-slate mt-2">Search flights, trains, buses or hotels and hold a fare. It shows up here.</p>
          <ButtonLink href="/search" className="mt-5">Find tickets</ButtonLink>
        </div>
      ) : null}
      {items?.length ? (
        <ul className="divide-y divide-rule border-y border-rule">
          {items.map((b) => {
            const Icon = KIND_ICON[b.kind];
            return (
              <li key={b.id}>
                <Link href={`/bookings/${b.id}`} className="grid grid-cols-[56px_1fr] sm:grid-cols-[64px_1fr_auto_auto] gap-5 py-5 items-center group">
                  <span className="h-14 w-14 rounded-sm bg-ink-soft flex items-center justify-center text-white shrink-0" aria-hidden>
                    <Icon size={22} />
                  </span>
                  <div className="min-w-0">
                    <h2 className="heading text-lg group-hover:underline underline-offset-4 decoration-signal decoration-[3px]">{b.title}</h2>
                    <p className="text-slate text-sm">
                      {b.provider_reference ? <span className="tabular font-bold text-ink">{b.provider_reference}, </span> : null}
                      made {shortDate(b.created_at)}
                    </p>
                  </div>
                  <span className={`col-start-2 sm:col-start-auto justify-self-start inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold ${STATUS[b.status].tone}`}>
                    {STATUS[b.status].label}
                  </span>
                  <span className="col-start-2 sm:col-start-auto heading text-lg tabular">{money(b.price)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </Page>
  );
}
