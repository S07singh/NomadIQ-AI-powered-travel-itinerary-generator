"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { DepartureBoard } from "@/components/trip/departure-board";
import { TripChat } from "@/components/trip/trip-chat";
import { TripHeading, TripView } from "@/components/trip/trip-view";
import { Button, Loading, Notice, Page } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { watchTripProgress } from "@/lib/progress";
import type { Trip, TripProgress } from "@/lib/types";

export default function TripPage() {
  const { id } = useParams<{ id: string }>();
  const user = useRequireUser();
  const router = useRouter();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [progress, setProgress] = useState<TripProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api
      .trip(id)
      .then((t) => {
        setTrip(t);
        setProgress(t.progress);
      })
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? "This trip doesn't exist or belongs to another account." : "Couldn't load this trip."));
  }, [id, user]);

  const busy = progress && (progress.status === "queued" || progress.status === "generating");

  useEffect(() => {
    if (!busy) return;
    return watchTripProgress(id, (p) => {
      setProgress(p);
      if (p.status === "ready" || p.status === "failed") api.trip(id).then(setTrip);
    });
  }, [busy, id]);

  if (error) return <Page className="py-16"><Notice>{error}</Notice></Page>;
  if (!user || !trip || !progress) return <Page><Loading label="Loading trip" /></Page>;

  const regenerate = async () => {
    const t = await api.regenerate(trip.id);
    setTrip(t);
    setProgress(t.progress);
  };
  const share = async () => {
    const res = await api.shareTrip(trip.id);
    const url = `${window.location.origin}/shared/${res.share_token}`;
    await navigator.clipboard?.writeText(url).catch(() => undefined);
    setShareUrl(url);
  };
  const remove = async () => {
    if (!window.confirm("Delete this trip? This can't be undone.")) return;
    await api.deleteTrip(trip.id);
    router.replace("/trips");
  };

  const ready = trip.status === "ready" && trip.plan;

  return (
    <Page>
      <TripHeading
        trip={trip}
        actions={
          ready ? (
            <>
              <Button variant="quiet" onClick={share}>Share</Button>
              <Button variant="quiet" onClick={regenerate}>Plan again</Button>
              <Button variant="danger" onClick={remove}>Delete</Button>
            </>
          ) : null
        }
      />
      {shareUrl ? (
        <div className="mb-6">
          <Notice tone="success">
            Link copied: <a className="underline break-all" href={shareUrl}>{shareUrl}</a>
          </Notice>
        </div>
      ) : null}

      {busy ? <DepartureBoard progress={progress} destination={trip.destination.split(",")[0]} /> : null}

      {progress.status === "failed" ? (
        <div className="max-w-[640px] space-y-4">
          <Notice>{trip.error === "interrupted" ? "Planning was interrupted by a server restart." : trip.error || "Planning failed."} Your inputs are saved.</Notice>
          <Button onClick={regenerate}>Try planning again</Button>
        </div>
      ) : null}

      {progress.status === "draft" ? (
        <div className="max-w-[640px] space-y-4">
          <p className="text-lg text-slate">This trip hasn&apos;t been planned yet.</p>
          <Button onClick={regenerate}>Draw the route</Button>
        </div>
      ) : null}

      {ready ? <TripView trip={trip} aside={<TripChat trip={trip} onUpdated={setTrip} />} /> : null}
    </Page>
  );
}
