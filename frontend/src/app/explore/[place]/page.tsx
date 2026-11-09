"use client";

import { MapPin, Play } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Photo } from "@/components/photo";
import { ButtonLink, Loading, Notice, Page } from "@/components/ui";
import { api } from "@/lib/api";
import { WEATHER_WORDS, shortDate, weekday } from "@/lib/format";
import type { DestinationOverview } from "@/lib/types";

export default function PlacePage() {
  const { place } = useParams<{ place: string }>();
  const name = decodeURIComponent(place);
  const [result, setResult] = useState<{ name: string; data?: DestinationOverview; failed?: boolean } | null>(null);

  useEffect(() => {
    api
      .destination(name)
      .then((data) => setResult({ name, data }))
      .catch(() => setResult({ name, failed: true }));
  }, [name]);

  const current = result?.name === name ? result : null;
  const data = current?.data ?? null;
  const error = !!current?.failed;

  if (error) return <Page className="py-16"><Notice>Couldn&apos;t load {name}. Check the spelling or try a nearby city.</Notice></Page>;
  if (!data) return <Page><Loading label={`Looking up ${name}`} /></Page>;

  const title = data.place?.name ?? name.split(",")[0];
  const where = [data.place?.region, data.place?.country].filter(Boolean).join(", ");
  const cover = data.images[0] ?? null;
  const gallery = data.images.slice(1, 7);

  return (
    <Page>
      <div className="mt-6 relative h-[46vh] min-h-[340px] max-h-[540px] overflow-hidden rounded-md bg-ink-soft">
        {cover ? <Photo image={cover} priority className="absolute inset-0 h-full w-full" /> : <div className="absolute inset-0 bg-gradient-to-br from-ink-soft to-board" aria-hidden />}
        <div className="absolute inset-0 hero-scrim" aria-hidden />
        <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8">
          <h1 className="editorial text-4xl sm:text-6xl text-white max-w-[18ch]">{title}</h1>
          {where ? <p className="mt-2 text-white/80 text-base sm:text-lg">{where}</p> : null}
        </div>
        {cover?.attribution ? <p className="absolute bottom-3 right-4 text-xs text-white/50">{cover.attribution}</p> : null}
      </div>
      <div className="flex flex-wrap justify-end gap-3 mt-4">
        <ButtonLink variant="quiet" href={`/search?tab=hotels&city=${encodeURIComponent(title)}`}>Find a place to stay</ButtonLink>
        <ButtonLink href={`/trips/new?to=${encodeURIComponent(name)}&days=4`}>Plan a trip here</ButtonLink>
      </div>

      <div className="mt-12 grid lg:grid-cols-[1fr_360px] gap-12">
        <div className="min-w-0">
          {data.summary?.summary ? (
            <>
              <p className="text-xl leading-relaxed max-w-[62ch]">{data.summary.summary}</p>
              {data.summary.url ? (
                <a href={data.summary.url} target="_blank" rel="noreferrer" className="mt-3 inline-block text-sm font-bold text-platform hover:underline underline-offset-4">
                  Read more on Wikipedia
                </a>
              ) : null}
            </>
          ) : null}

          {gallery.length ? (
            <div className="mt-10 grid grid-cols-2 sm:grid-cols-3 auto-rows-[150px] sm:auto-rows-[180px] gap-1.5 rounded-md overflow-hidden">
              {gallery.map((img) => (
                <Photo key={img.url} image={img} className="group [&>img]:transition-transform [&>img]:duration-700 [&>img]:ease-out hover:[&>img]:scale-105" />
              ))}
            </div>
          ) : null}

          {data.weather.length ? (
            <section className="mt-12">
              <h2 className="heading text-2xl mb-4">This week&apos;s weather</h2>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] tabular text-center">
                  <caption className="sr-only">Seven-day forecast</caption>
                  <thead>
                    <tr className="border-b-2 border-ink">
                      {data.weather.map((w) => (
                        <th key={w.date} scope="col" className="py-2 font-bold">
                          {weekday(w.date)}
                          <span className="block text-xs text-slate font-normal">{shortDate(w.date)}</span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      {data.weather.map((w) => (
                        <td key={w.date} className="py-3">
                          <span className="heading text-xl block">{w.temp_max_c != null ? `${Math.round(w.temp_max_c)}°` : ""}</span>
                          <span className="text-slate text-sm block">{w.temp_min_c != null ? `${Math.round(w.temp_min_c)}°` : ""}</span>
                          <span className="text-sm block mt-1">{WEATHER_WORDS[w.condition]}</span>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </div>

        <aside className="space-y-8">
          <a href={data.maps_url} target="_blank" rel="noreferrer" className="flex items-center gap-2 font-bold text-platform hover:underline underline-offset-4">
            <MapPin size={18} aria-hidden /> Open in Google Maps
          </a>
          {data.videos.length ? (
            <div>
              <h2 className="heading text-lg mb-3">Videos</h2>
              <ul className="space-y-2">
                {data.videos.map((v) => (
                  <li key={v.url}>
                    <a href={v.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 font-semibold text-platform hover:underline underline-offset-4">
                      <Play size={16} aria-hidden /> {v.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </aside>
      </div>
    </Page>
  );
}
