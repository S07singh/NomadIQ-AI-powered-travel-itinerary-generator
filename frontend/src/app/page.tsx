import Link from "next/link";
import { HeroRoute } from "@/components/hero-route";
import { PlacePhoto } from "@/components/photo";
import { PlannerSentence } from "@/components/planner-sentence";
import { Page } from "@/components/ui";

const PLACES = [
  { name: "Jaipur", query: "Hawa Mahal Jaipur", note: "Best from November to February. Four days covers the forts and bazaars." },
  { name: "Hampi", query: "Hampi Virupaksha Temple", note: "Boulders and ruins. Go in winter, stay near Hampi Bazaar." },
  { name: "Kyoto", query: "Fushimi Inari Kyoto", note: "Shrines at dawn, markets at noon. Spring and autumn book up early." },
  { name: "Munnar", query: "Munnar tea plantations", note: "Tea estates and cool air. Three days, ideally by road from Kochi." },
  { name: "Lisbon", query: "Alfama Lisbon", note: "Hills, trams, custard tarts. Pleasant almost all year." },
];

const STEPS = [
  { title: "Give us the outline", body: "Where, how long, roughly what you want to spend. Sights, stays and food are researched side by side, then stitched into days." },
  { title: "Shape it by talking", body: "Swap a day, make it cheaper, add a night market. Type it or say it, and the route redraws." },
  { title: "Book the seats", body: "Live fares for flights, trains, buses and hotels. Nothing is booked until you confirm the final price." },
];

export default function Home() {
  return (
    <>
      <section className="border-b border-rule bg-sheet">
        <Page className="grid lg:grid-cols-[1.25fr_1fr] gap-12 lg:gap-6 pt-12 pb-16 sm:pt-16 sm:pb-20 items-center">
          <div>
            <h1 className="display text-[2.9rem] sm:text-[4.4rem] max-w-[13ch]">Plan the trip. Book the seats.</h1>
            <p className="mt-5 mb-10 text-lg sm:text-xl text-slate max-w-[48ch]">
              A day-by-day route with photos, weather and real prices, and the tickets to get there.
            </p>
            <PlannerSentence />
          </div>
          <div className="hidden sm:flex justify-center lg:justify-end">
            <HeroRoute />
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
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-x-5 gap-y-8">
            {PLACES.map((p, i) => (
              <Link
                key={p.name}
                href={`/explore/${encodeURIComponent(p.name)}`}
                className={i === 0 ? "col-span-2 lg:col-span-3 lg:row-span-2 group" : "col-span-1 lg:col-span-3 xl:col-span-3 group"}
              >
                <PlacePhoto query={p.query} className={i === 0 ? "aspect-[4/3] lg:aspect-auto lg:h-[calc(100%-5.5rem)] rounded-sm" : "aspect-[16/10] rounded-sm"} />
                <h3 className="mt-3 heading text-xl group-hover:underline underline-offset-4 decoration-signal decoration-[3px]">{p.name}</h3>
                <p className="text-slate text-[0.95rem] max-w-[46ch]">{p.note}</p>
              </Link>
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
        <Page className="pt-24">
          <div className="bg-ink text-white rounded-md px-6 py-10 sm:px-12 sm:py-14 grid md:grid-cols-[1fr_auto] gap-8 items-center">
            <div>
              <h2 className="heading text-3xl sm:text-4xl max-w-[20ch]">&ldquo;Find me a sleeper to Goa on Friday.&rdquo;</h2>
              <p className="mt-4 text-white/75 text-lg max-w-[52ch]">
                Ask the assistant in English or Hindi, by typing or holding the mic. It searches, compares and holds the fare. You tap confirm.
              </p>
            </div>
            <Link href="/assistant" className="inline-flex h-12 items-center rounded-md bg-signal px-6 font-extrabold text-ink hover:bg-signal-deep">
              Talk to the assistant
            </Link>
          </div>
        </Page>
      </section>
    </>
  );
}
