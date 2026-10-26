"use client";

import { useState } from "react";
import { shortDate, weekday } from "@/lib/format";
import type { FlightOffer, Trip } from "@/lib/types";
import { Checkout } from "../checkout";
import { ExternalBook } from "../external-book";
import { OfferRow } from "../offers";
import { Button } from "../ui";

function Leg({ title, date, offers, tripId }: { title: string; date?: string | null; offers: FlightOffer[]; tripId: string }) {
  const [selected, setSelected] = useState<string | null>(null);
  if (!offers.length) return null;
  return (
    <section className="mb-10">
      <h3 className="heading text-xl mb-2">
        {title}
        {date ? <span className="text-slate font-semibold text-base ml-3">{weekday(date)} {shortDate(date)}</span> : null}
      </h3>
      <ul className="divide-y divide-rule border-y border-rule">
        {offers.map((offer) => (
          <li key={offer.offer_id} className="py-5">
            <OfferRow
              offer={offer}
              action={
                offer.bookable ? (
                  selected === offer.offer_id ? null : <Button variant="quiet" onClick={() => setSelected(offer.offer_id)}>Select</Button>
                ) : (
                  <ExternalBook offer={offer} />
                )
              }
            />
            {selected === offer.offer_id ? <Checkout offer={offer} tripId={tripId} onClose={() => setSelected(null)} /> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function FlightsSection({ trip }: { trip: Trip }) {
  const f = trip.plan?.flights;
  if (!f) return null;
  const from = f.origin_airport;
  const to = f.destination_airport;
  return (
    <div>
      {from && to ? (
        <p className="text-lg mb-6">
          <span className="heading">{from.iata_code}</span> {from.name} <span aria-hidden className="mx-2 text-slate">to</span>
          <span className="heading">{to.iata_code}</span> {to.name}
        </p>
      ) : null}
      {f.note ? <p className="text-slate mb-6 max-w-[60ch]">{f.note}</p> : null}
      <Leg title="Going" date={trip.start_date} offers={f.outbound} tripId={trip.id} />
      <Leg title="Coming back" date={trip.end_date} offers={f.inbound} tripId={trip.id} />
      {f.links.length ? (
        <p className="text-slate">
          Compare more fares on{" "}
          {f.links.map((l, i) => (
            <span key={l.url}>
              {i ? " or " : ""}
              <a href={l.url} target="_blank" rel="noreferrer" className="font-bold text-platform hover:underline underline-offset-4">{l.label}</a>
            </span>
          ))}
          . Prices change often; the final price is confirmed before you pay.
        </p>
      ) : null}
    </div>
  );
}
