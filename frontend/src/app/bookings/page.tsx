"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ButtonLink, Loading, Notice, Page, PageTitle } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { money, shortDate } from "@/lib/format";
import type { BookingStatus, BookingSummary } from "@/lib/types";

const STATUS: Record<BookingStatus, { label: string; tone: string }> = {
  awaiting_confirmation: { label: "Waiting for payment", tone: "text-ink" },
  processing: { label: "Confirming", tone: "text-slate" },
  confirmed: { label: "Confirmed", tone: "text-platform-deep" },
  failed: { label: "Failed, refunded", tone: "text-brick" },
  cancelled: { label: "Cancelled", tone: "text-slate" },
  expired: { label: "Hold expired", tone: "text-slate" },
};

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
        <table className="w-full tabular">
          <caption className="sr-only">Your bookings</caption>
          <thead>
            <tr className="text-left text-slate text-sm border-b-2 border-ink">
              <th className="py-2 font-bold">Booking</th>
              <th className="py-2 font-bold hidden sm:table-cell">Reference</th>
              <th className="py-2 font-bold">Status</th>
              <th className="py-2 font-bold text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {items.map((b) => (
              <tr key={b.id} className="border-b border-rule">
                <td className="py-4 pr-4">
                  <Link href={`/bookings/${b.id}`} className="font-bold hover:underline underline-offset-4">{b.title}</Link>
                  <span className="block text-sm text-slate capitalize">{b.kind}, made {shortDate(b.created_at)}</span>
                </td>
                <td className="py-4 pr-4 hidden sm:table-cell font-bold">{b.provider_reference ?? ""}</td>
                <td className={`py-4 pr-4 font-bold ${STATUS[b.status].tone}`}>{STATUS[b.status].label}</td>
                <td className="py-4 text-right font-bold">{money(b.price)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </Page>
  );
}
