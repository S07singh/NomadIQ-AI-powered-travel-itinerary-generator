import { dateRange } from "@/lib/format";
import type { Trip } from "@/lib/types";
import { Photo } from "../photo";

/**
 * The trip page's photo banner: one strong cover photo (not a mosaic of thumbnails — those
 * belong in the Sights tab, in context) with the destination name set directly on it, echoing
 * the homepage hero and destination tiles. `actions` (Share/Plan again/Delete) sit in a quiet
 * row underneath rather than cluttering the photo itself.
 */
export function TripBanner({ trip, actions }: { trip: Trip; actions?: React.ReactNode }) {
  const plan = trip.plan!;
  const people = trip.travelers.adults + trip.travelers.children;
  const image = plan.cover_image ?? plan.gallery[0] ?? null;

  return (
    <div className="mt-6">
      <div className="relative h-[42vh] min-h-[320px] max-h-[520px] overflow-hidden rounded-md bg-ink-soft">
        {image ? <Photo image={image} priority className="absolute inset-0 h-full w-full" /> : <div className="absolute inset-0 bg-gradient-to-br from-ink-soft to-board" aria-hidden />}
        <div className="absolute inset-0 hero-scrim" aria-hidden />
        <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8">
          <h1 className="editorial text-4xl sm:text-6xl text-white max-w-[18ch]">{trip.destination.split(",")[0]}</h1>
          <p className="mt-2 text-white/80 text-base sm:text-lg">
            {dateRange(trip.start_date, trip.end_date)}, {trip.duration_days} days, {people} {people === 1 ? "traveler" : "travelers"}
            {trip.origin ? `, from ${trip.origin}` : ""}
          </p>
        </div>
        {image?.attribution ? <p className="absolute bottom-3 right-4 text-xs text-white/50">{image.attribution}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap justify-end gap-3 mt-4">{actions}</div> : null}
    </div>
  );
}
