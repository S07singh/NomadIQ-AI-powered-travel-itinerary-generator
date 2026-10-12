import { Star } from "lucide-react";
import type { ReactNode } from "react";
import { clock, duration, money, shortDate } from "@/lib/format";
import type { ActivityOffer, AnyOffer, FlightOffer, HotelOffer, TransportOffer } from "@/lib/types";
import { Photo } from "./photo";

function Price({ offer, note, action, sub }: { offer: AnyOffer; note?: string; action?: ReactNode; sub?: ReactNode }) {
  return (
    <div className="flex md:flex-col items-center md:items-end justify-between gap-3">
      <p className="md:text-right">
        <span className="heading text-2xl tabular block">{money(offer.price)}</span>
        <span className="text-sm text-slate tabular">{sub ?? note ?? (offer.refundable ? "Refundable" : "Non-refundable")}</span>
      </p>
      {action}
    </div>
  );
}

function Times({ dep, arr, from, to, mins, stops }: { dep: string; arr: string; from: string; to: string; mins: number; stops?: number }) {
  const nextDay = arr.slice(0, 10) > dep.slice(0, 10);
  return (
    <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 tabular">
      <div>
        <p className="heading text-2xl">{clock(dep)}</p>
        <p className="text-sm font-bold text-slate">{from}</p>
      </div>
      <div className="text-center text-sm text-slate px-1">
        <span className="block">{duration(mins)}</span>
        <span className="block h-[3px] bg-ink/80 rounded-full my-1 relative">
          {stops ? <span className="absolute left-1/2 -translate-x-1/2 -top-[4px] w-[11px] h-[11px] rounded-full bg-sheet border-2 border-ink" /> : null}
        </span>
        <span className="block">{stops === undefined ? "" : stops === 0 ? "Direct" : `${stops} stop${stops > 1 ? "s" : ""}`}</span>
      </div>
      <div className="text-right">
        <p className="heading text-2xl">
          {clock(arr)}
          {nextDay ? <sup className="text-xs text-brick font-bold ml-0.5">+1</sup> : null}
        </p>
        <p className="text-sm font-bold text-slate">{to}</p>
      </div>
    </div>
  );
}

export function FlightRow({ offer, action }: { offer: FlightOffer; action?: ReactNode }) {
  const carriers = Array.from(new Set(offer.slices.flatMap((s) => s.segments.map((g) => g.carrier))));
  return (
    <div className="grid md:grid-cols-[1fr_160px] gap-5 items-center">
      <div className="space-y-4">
        {offer.slices.map((s, i) => (
          <div key={i} className="grid sm:grid-cols-[150px_1fr] gap-3 items-center">
            <p className="text-sm text-slate">
              <span className="font-bold text-ink">{i === 0 ? "Out" : "Back"}</span> {shortDate(s.departure_at)}
              <span className="block">{s.segments.map((g) => g.flight_number).join(", ")}</span>
            </p>
            <Times dep={s.departure_at} arr={s.arrival_at} from={s.origin} to={s.destination} mins={s.duration_minutes} stops={s.stops} />
          </div>
        ))}
        <p className="text-sm text-slate">
          {carriers.join(", ")}, {offer.cabin_class.replace("_", " ")}
          {offer.baggage ? `, ${offer.baggage}` : ""}
        </p>
      </div>
      <Price offer={offer} action={action} note={`${offer.passengers} traveler${offer.passengers > 1 ? "s" : ""}, total`} />
    </div>
  );
}

export function TransportRow({ offer, action }: { offer: TransportOffer; action?: ReactNode }) {
  return (
    <div className="grid md:grid-cols-[1fr_160px] gap-5 items-center">
      <div className="grid sm:grid-cols-[200px_1fr] gap-4 items-center">
        <div>
          <p className="font-extrabold">{offer.service_name}</p>
          <p className="text-sm text-slate tabular">
            {offer.kind === "train" ? `No. ${offer.service_number}` : offer.operator}, {offer.travel_class}
          </p>
          {offer.seats_available != null ? (
            <p className={`text-sm font-bold ${offer.seats_available < 10 ? "text-brick" : "text-platform-deep"}`}>
              {offer.seats_available === 0 ? "Waitlist" : `${offer.seats_available} seats left`}
            </p>
          ) : null}
        </div>
        <Times dep={offer.departure_at} arr={offer.arrival_at} from={offer.origin} to={offer.destination} mins={offer.duration_minutes} />
      </div>
      <Price offer={offer} action={action} />
    </div>
  );
}

export function HotelRow({ offer, action }: { offer: HotelOffer; action?: ReactNode }) {
  return (
    <div className="grid sm:grid-cols-[180px_1fr_auto] gap-5">
      <Photo image={offer.images[0]} alt={offer.name} className="aspect-[4/3] rounded-sm" />
      <div>
        <p className="heading text-xl">{offer.name}</p>
        <p className="text-sm text-slate flex items-center gap-1">
          {offer.star_rating ? (
            <span className="inline-flex" aria-label={`${offer.star_rating} stars`}>
              {Array.from({ length: Math.round(offer.star_rating) }).map((_, i) => (
                <Star key={i} size={13} className="fill-signal stroke-signal-deep" aria-hidden />
              ))}
            </span>
          ) : null}
          {offer.review_score ? <span className="tabular ml-1">{offer.review_score.toFixed(1)} guest score</span> : null}
        </p>
        <p className="mt-2">{offer.room_name}{offer.board_type === "breakfast_included" ? ", breakfast included" : ""}</p>
        <p className="text-sm text-slate">{offer.cancellation_policy ?? (offer.refundable ? "Refundable" : "Non-refundable")}</p>
        {offer.amenities.length ? <p className="text-sm text-slate mt-1">{offer.amenities.slice(0, 5).join(", ")}</p> : null}
      </div>
      <Price offer={offer} action={action} sub={`${offer.nights} night${offer.nights > 1 ? "s" : ""}, ${money(offer.price_per_night)} each`} />
    </div>
  );
}

export function ActivityRow({ offer, action }: { offer: ActivityOffer; action?: ReactNode }) {
  return (
    <div className="grid sm:grid-cols-[180px_1fr_160px] gap-5">
      <Photo image={offer.images[0]} alt={offer.name} className="aspect-[4/3] rounded-sm" />
      <div>
        <p className="heading text-xl">{offer.name}</p>
        <p className="text-slate mt-1 max-w-[60ch]">{offer.description}</p>
        <p className="text-sm text-slate mt-1 tabular">
          {[offer.duration_minutes ? duration(offer.duration_minutes) : null, offer.rating ? `${offer.rating} from ${offer.review_count} reviews` : null].filter(Boolean).join(", ")}
        </p>
      </div>
      <Price offer={offer} action={action} note="a person" />
    </div>
  );
}

export function OfferRow({ offer, action }: { offer: AnyOffer; action?: ReactNode }) {
  switch (offer.kind) {
    case "flight":
      return <FlightRow offer={offer} action={action} />;
    case "hotel":
      return <HotelRow offer={offer} action={action} />;
    case "train":
    case "bus":
      return <TransportRow offer={offer} action={action} />;
    case "activity":
      return <ActivityRow offer={offer} action={action} />;
  }
}
