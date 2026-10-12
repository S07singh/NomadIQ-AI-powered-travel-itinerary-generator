"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { OfferRow } from "@/components/offers";
import { Button, ButtonLink, Loading, Notice, Page } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { money } from "@/lib/format";
import type { Booking } from "@/lib/types";

function useCountdown(until?: string | null) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!until) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [until]);
  if (!until) return null;
  const ms = new Date(until).getTime() - now;
  if (ms <= 0) return "expired";
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}:${String(s).padStart(2, "0")}`;
}

const HEADLINES: Record<Booking["status"], string> = {
  awaiting_confirmation: "Review and pay",
  processing: "Confirming with the supplier",
  confirmed: "You're booked",
  failed: "Booking didn't go through",
  cancelled: "Booking cancelled",
  expired: "Price hold expired",
};

export default function BookingPage() {
  const { id } = useParams<{ id: string }>();
  const user = useRequireUser();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const left = useCountdown(booking?.status === "awaiting_confirmation" ? booking.confirm_before : null);

  useEffect(() => {
    if (user) api.booking(id).then(setBooking).catch(() => setError("This booking doesn't exist or belongs to another account."));
  }, [id, user]);

  if (!booking) return <Page className="py-16">{error ? <Notice>{error}</Notice> : <Loading label="Loading booking" />}</Page>;

  const act = async (fn: () => Promise<Booking>) => {
    setBusy(true);
    setError(null);
    try {
      setBooking(await fn());
    } catch (err) {
      if (err instanceof ApiError && err.code === "price_mismatch") {
        setBooking(await api.booking(id));
        setError("The price changed while you were deciding. Check the new total before paying.");
      } else setError(err instanceof ApiError ? err.message : "That didn't work. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const confirm = () => act(() => api.confirmBooking(booking.id, booking.price, "tok_web_demo"));
  const cancel = () => {
    if (window.confirm(booking.status === "confirmed" ? "Cancel this booking? Refund depends on the fare rules." : "Release this price hold?")) act(() => api.cancelBooking(booking.id));
  };

  return (
    <Page className="pb-10">
      <header className="pt-10 pb-8">
        <p className="font-semibold text-slate">{booking.kind[0].toUpperCase() + booking.kind.slice(1)} booking</p>
        <h1 className="display text-4xl sm:text-5xl mt-1">{HEADLINES[booking.status]}</h1>
      </header>

      <div className="grid lg:grid-cols-[1fr_340px] gap-12">
        <div>
          {booking.status === "confirmed" ? (
            <div className="mb-8 bg-board text-white rounded-md px-6 py-5 flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-white/70">Booking reference</p>
                <p className="heading text-4xl tabular text-signal tracking-wide">{booking.provider_reference}</p>
              </div>
              {booking.tickets.length ? <p className="text-white/70 tabular text-right">Tickets {booking.tickets.join(", ")}</p> : null}
            </div>
          ) : null}
          <section className="border-y border-rule py-6">
            <OfferRow offer={booking.offer} />
          </section>
          <section className="mt-8">
            <h2 className="heading text-xl mb-3">Travelers</h2>
            <ul className="space-y-1">
              {booking.travelers.map((t, i) => (
                <li key={i}>
                  {t.given_name} {t.family_name}
                  {t.born_on ? <span className="text-slate">, born {t.born_on}</span> : null}
                </li>
              ))}
            </ul>
            {booking.contact ? <p className="mt-3 text-slate">Tickets go to {booking.contact.email}, updates to {booking.contact.phone}.</p> : null}
          </section>
        </div>

        <aside className="lg:sticky lg:top-24 self-start border-l-4 border-signal pl-6 space-y-4">
          <div>
            <p className="text-slate">Total</p>
            <p className="display text-5xl tabular">{money(booking.price)}</p>
            {booking.price_changed && booking.original_price ? (
              <p className="text-brick font-bold mt-1">Was {money(booking.original_price)} when you searched.</p>
            ) : null}
          </div>
          {error ? <Notice>{error}</Notice> : null}
          {booking.failure_reason && booking.status !== "awaiting_confirmation" ? <Notice>{booking.failure_reason}</Notice> : null}

          {booking.status === "awaiting_confirmation" ? (
            <>
              {left && left !== "expired" ? <p className="text-slate tabular">Price held for {left}</p> : null}
              {left === "expired" ? <Notice>The hold has run out. Search again for a fresh price.</Notice> : null}
              <Button onClick={confirm} disabled={busy || left === "expired"} className="w-full">
                {busy ? "Paying and booking" : `Pay ${money(booking.price)} and book`}
              </Button>
              <Button variant="quiet" onClick={cancel} disabled={busy} className="w-full">Release hold</Button>
              <p className="text-sm text-slate">Test mode: payments are simulated until a payment provider is connected.</p>
            </>
          ) : null}
          {booking.status === "confirmed" ? (
            <Button variant="danger" onClick={cancel} disabled={busy} className="w-full">Cancel booking</Button>
          ) : null}
          {booking.status === "expired" || booking.status === "failed" ? <ButtonLink href={`/search?tab=${booking.kind === "activity" ? "activities" : booking.kind + "s"}`} className="w-full">Search again</ButtonLink> : null}
          <Link href="/bookings" className="block font-bold text-platform hover:underline underline-offset-4">All bookings</Link>
        </aside>
      </div>
    </Page>
  );
}
