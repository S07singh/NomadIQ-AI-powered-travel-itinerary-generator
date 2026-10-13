"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { TripHeading, TripView } from "@/components/trip/trip-view";
import { ButtonLink, Loading, Notice, Page } from "@/components/ui";
import { api } from "@/lib/api";
import type { Trip } from "@/lib/types";

export default function SharedTripPage() {
  const { token } = useParams<{ token: string }>();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    api.sharedTrip(token).then(setTrip).catch(() => setMissing(true));
  }, [token]);

  if (missing) return <Page className="py-16"><Notice>This share link has been turned off or never existed.</Notice></Page>;
  if (!trip) return <Page><Loading label="Loading shared trip" /></Page>;

  return (
    <Page>
      <TripHeading trip={trip} actions={<ButtonLink href={`/trips/new?to=${encodeURIComponent(trip.destination)}&days=${trip.duration_days}`}>Plan a trip like this</ButtonLink>} />
      <TripView trip={trip} />
    </Page>
  );
}
