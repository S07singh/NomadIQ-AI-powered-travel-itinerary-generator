import Link from "next/link";
import { AssistantTeaser } from "@/components/assistant-teaser";
import { HeroRoute } from "@/components/hero-route";
import { Hero } from "@/components/hero";
import { PlaceTile } from "@/components/place-tile";
import { Page } from "@/components/ui";
import { api } from "@/lib/api";
import { HERO_SLIDES } from "@/lib/hero-slides";
import type { MediaImage } from "@/lib/types";

// Deliberately distinct from HERO_SLIDES so a visitor never sees the same photo twice
// between the top of the page and this grid.
const PLACES = [
  { name: "Udaipur", query: "City Palace Udaipur Lake Pichola", note: "Lakes and palaces. Best October to March, three or four days." },
  { name: "Rishikesh", query: "Lakshman Jhula Rishikesh Ganges", note: "Rafting by day, ghats at dusk. Quiet outside the May rush." },
  { name: "Varanasi", query: "Varanasi ghats Ganges sunrise", note: "Boats at dawn on the ghats. Go for the mornings, stay for the lanes." },
  { name: "Munnar", query: "Munnar tea plantations", note: "Tea estates and cool air. Three days, ideally by road from Kochi." },
  { name: "Lisbon", query: "Alfama Lisbon", note: "Hills, trams, custard tarts. Pleasant almost all year." },
];

const STEPS = [
  { title: "Give us the outline", body: "Where, how long, roughly what you want to spend. Sights, stays and food are researched side by side, then stitched into days." },
  { title: "Shape it by talking", body: "Swap a day, make it cheaper, add a night market. Type it or say it, and the route redraws." },
  { title: "Book the seats", body: "Live fares for flights, trains, buses and hotels. Nothing is booked until you confirm the final price." },
];

// Re-fetched in the background at most once an hour — curated destination photos don't need
// to be any fresher than that, and this keeps the homepage served from the prerendered cache.
export const revalidate = 3600;

// A failed lookup must never take the homepage down with it.
async function firstImage(query: string): Promise<MediaImage | null> {
  try {
    const images = await api.images(query, 1);
    return images[0] ?? null;
  } catch {
    return null;
  }
}

export default async function Home() {
  // Resolved on the server, before any HTML ships, so neither the hero nor the destination
  // grid ever shows a client-side loading flash — the page arrives with real photos already in it.
  const [heroImages, placeImages] = await Promise.all([
    Promise.all(HERO_SLIDES.map((s) => firstImage(s.query))),
    Promise.all(PLACES.map((p) => firstImage(p.query))),
  ]);

  return (
    <>
      <Hero images={heroImages} />

      <section className="border-b border-rule bg-sheet">
        <Page className="grid lg:grid-cols-[1fr_1.2fr] gap-12 lg:gap-16 py-16 sm:py-20 items-center">
          <div className="order-2 lg:order-1 flex justify-center lg:justify-start">
            <HeroRoute />
          </div>
          <div className="order-1 lg:order-2">
            <p className="editorial text-3xl sm:text-4xl text-ink mb-5">This is what you actually get.</p>
            <p className="text-lg text-slate max-w-[52ch] leading-relaxed">
              Not a wall of text — a route. Every day is a stop with a time, a place and a price, pulled from real research and live fares, so you can see the whole trip before you&apos;ve booked a single seat.
            </p>
          </div>
        </Page>
      </section>

      <section>
        <Page className="pt-16 sm:pt-20">
          <div className="flex items-end justify-between gap-6 mb-8">
            <h2 className="heading text-3xl sm:text-4xl">Where people are going</h2>
            <Link href="/explore" className="font-bold text-platform hover:underline underline-offset-4 shrink-0">
              Explore a place
            </Link>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
            {PLACES.map((p, i) => (
              <PlaceTile
                key={p.name}
                name={p.name}
                note={p.note}
                image={placeImages[i]}
                priority
                className={i === 0 ? "col-span-2 lg:col-span-3 lg:row-span-2 aspect-[4/3] lg:aspect-auto" : "col-span-1 lg:col-span-3 aspect-[16/11]"}
              />
            ))}
          </div>
        </Page>
      </section>

      <section>
        <Page className="pt-24">
          <h2 className="heading text-3xl sm:text-4xl max-w-[22ch]">From a rough idea to a seat number</h2>
          <ol className="mt-12 relative grid md:grid-cols-3 gap-10 md:gap-8">
            <span aria-hidden className="hidden md:block absolute left-2 right-[30%] top-[7px] h-[6px] rounded-full bg-signal" />
            {STEPS.map((s, i) => (
              <li key={s.title} className="relative">
                <span aria-hidden className={`block w-5 h-5 rounded-full border-[4px] border-ink ${i === 2 ? "bg-sheet" : "bg-signal"}`} />
                <h3 className="heading text-xl mt-5">{s.title}</h3>
                <p className="mt-2 text-slate max-w-[38ch]">{s.body}</p>
              </li>
            ))}
          </ol>
        </Page>
      </section>

      <section>
        <Page className="py-24">
          <AssistantTeaser />
        </Page>
      </section>
    </>
  );
}
