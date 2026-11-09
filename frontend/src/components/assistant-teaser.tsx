import Link from "next/link";

// A fabricated but representative exchange — the same departure-board chrome used while a
// trip is actually generating, so this reads as "I've seen this screen work" not a mockup.
const ROWS = [
  { text: "Find me a sleeper to Goa on Friday", who: "you" },
  { text: "Held: Zingbus AC Sleeper, 21:30, ₹1,240", who: "assistant" },
  { text: "Make it two days earlier and vegetarian-friendly", who: "you" },
];

export function AssistantTeaser() {
  return (
    <div className="bg-board text-white rounded-md overflow-hidden grid md:grid-cols-[1fr_auto] gap-8 md:gap-10 items-center px-6 py-10 sm:px-10 sm:py-12">
      <div>
        <p className="font-bold text-signal mb-5">Ask it like you&apos;d ask a friend</p>
        <ul className="space-y-3 tabular max-w-[46ch]">
          {ROWS.map((r, i) => (
            <li key={i} className={r.who === "you" ? "text-white/90" : "text-white/60"}>
              <span className="font-bold mr-2">{r.who === "you" ? "You" : "It"}</span>
              {r.text}
            </li>
          ))}
        </ul>
        <p className="mt-6 text-white/70 max-w-[50ch]">
          Type it or hold the mic, in English or Hindi. It searches, compares and holds the fare — you confirm the price before anything is booked.
        </p>
      </div>
      <Link href="/assistant" className="inline-flex h-12 shrink-0 items-center rounded-md bg-signal px-6 font-extrabold text-ink hover:bg-signal-deep">
        Talk to the assistant
      </Link>
    </div>
  );
}
