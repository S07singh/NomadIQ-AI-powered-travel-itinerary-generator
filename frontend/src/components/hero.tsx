"use client";

/* eslint-disable @next/next/no-img-element -- photos are live Wikimedia URLs, not local assets */
import { useEffect, useState } from "react";
import { PlannerSentence } from "./planner-sentence";
import { HERO_SLIDES } from "@/lib/hero-slides";
import type { MediaImage } from "@/lib/types";

// Images are fetched server-side (see page.tsx) and handed to this component already
// resolved, so the hero never shows a loading state; this component only owns the
// crossfade timing for the five real, highly photographed places in HERO_SLIDES.
const SLIDE_MS = 6500;

export function Hero({ images }: { images: (MediaImage | null)[] }) {
  const [index, setIndex] = useState(0);
  // Bumped alongside `index` so the active slide's <img> remounts each time it reactivates,
  // restarting the one-shot Ken Burns drift (a React key change is the only reliable way).
  const [cycle, setCycle] = useState(0);
  const usable = HERO_SLIDES.map((s, i) => ({ ...s, image: images[i] })).filter((s) => s.image);

  useEffect(() => {
    if (usable.length < 2) return;
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % usable.length);
      setCycle((c) => c + 1);
    }, SLIDE_MS);
    return () => clearInterval(id);
  }, [usable.length]);

  const activeSlide = usable[index % Math.max(usable.length, 1)];

  return (
    <section className="relative h-[86vh] min-h-[600px] max-h-[920px] w-full overflow-hidden bg-board">
      {usable.map((s, i) => (
        <div key={i} className="absolute inset-0 transition-opacity duration-[1400ms] ease-in-out" style={{ opacity: i === index ? 1 : 0 }} aria-hidden={i !== index}>
          <img
            key={i === index ? `${i}-${cycle}` : i}
            src={s.image!.url}
            alt=""
            fetchPriority={i === 0 ? "high" : "auto"}
            className={i === index ? "hero-drift h-full w-full object-cover" : "h-full w-full object-cover"}
          />
        </div>
      ))}
      <div className="absolute inset-0 hero-scrim" aria-hidden />

      <div className="relative z-10 flex h-full flex-col justify-end">
        <div className="mx-auto w-full max-w-[1180px] px-4 pb-14 sm:px-6 sm:pb-20 lg:px-8">
          <p className="editorial text-[2.6rem] sm:text-[3.6rem] lg:text-[4.3rem] text-white max-w-[15ch]">Plan the trip. Book the seats.</p>
          <p className="mt-4 mb-9 text-lg sm:text-xl text-white/80 max-w-[48ch]">
            A day-by-day route with photos, weather and real prices, and the tickets to get there.
          </p>
          <PlannerSentence tone="light" />
        </div>
      </div>

      {activeSlide ? (
        <p className="absolute bottom-3 right-4 z-10 text-xs text-white/50">
          {activeSlide.image!.attribution} — {activeSlide.credit}
        </p>
      ) : null}
    </section>
  );
}
