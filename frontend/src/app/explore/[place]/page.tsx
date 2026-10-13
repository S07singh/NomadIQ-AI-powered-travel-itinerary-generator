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

  return (
    <Page>
      <header className="pt-10 pb-8 flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="display text-5xl sm:text-7xl">{title}</h1>
          {where ? <p className="mt-2 text-lg text-slate">{where}</p> : null}
        </div>
        <div className="flex flex-wrap gap-3">
          <ButtonLink href={`/trips/new?to=${encodeURIComponent(name)}&days=4`}>Plan a trip here</ButtonLink>
          <ButtonLink variant="quiet" href={`/search?tab=hotels&city=${encodeURIComponent(title)}`}>Find a place to stay</ButtonLink>
        </div>
      </header>

      {data.images.length ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 auto-rows-[150px] sm:auto-rows-[190px] gap-1.5 rounded-md overflow-hidden">
          {data.images.slice(0, 7).map((img, i) => (
            <Photo key={img.url} image={img} className={i === 0 ? "col-span-2 row-span-2" : i === 3 ? "sm:col-span-2" : ""} credit={i === 0} />
          ))}
        </div>
      ) : null}

      <div className="mt-12 grid lg:grid-cols-[1fr_360px] gap-12">
        <div>
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
