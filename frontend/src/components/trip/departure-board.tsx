import clsx from "clsx";
import type { TripProgress } from "@/lib/types";

const ROWS = [
  { step: "research", label: "Sights, stays and food" },
  { step: "itinerary", label: "Day-by-day route" },
  { step: "enrich", label: "Photos, maps, weather" },
  { step: "done", label: "Ready to view" },
];
const ORDER = ["queued", "research", "itinerary", "enrich", "done"];

/** Generation progress shown as a station departure board. */
export function DepartureBoard({ progress, destination }: { progress: TripProgress; destination: string }) {
  const current = ORDER.indexOf(progress.step || "queued");
  return (
    <section aria-live="polite" className="bg-board text-white rounded-md overflow-hidden max-w-[720px]">
      <div className="flex items-baseline justify-between gap-4 px-5 sm:px-7 pt-6 pb-4 border-b border-white/15">
        <h2 className="heading text-2xl text-signal">Now planning: {destination}</h2>
        <span className="tabular text-white/60">{progress.percent}%</span>
      </div>
      <table className="w-full text-left tabular">
        <caption className="sr-only">Planning steps</caption>
        <tbody>
          {ROWS.map((row) => {
            const index = ORDER.indexOf(row.step);
            const state = index < current ? "Done" : index === current ? "Now" : "Next";
            return (
              <tr key={row.step} className="border-b border-white/10 last:border-0">
                <td className="px-5 sm:px-7 py-3.5 text-lg font-semibold">{row.label}</td>
                <td className="px-5 sm:px-7 py-3.5 text-right w-28">
                  <span
                    key={state}
                    className={clsx(
                      "flap inline-block min-w-16 text-center rounded-xs px-2 py-0.5 font-extrabold",
                      state === "Done" && "bg-platform text-white",
                      state === "Now" && "bg-signal text-ink",
                      state === "Next" && "text-white/45",
                    )}
                  >
                    {state}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="px-5 sm:px-7 py-4 text-white/70 border-t border-white/15">{progress.message || "Queued"}</p>
    </section>
  );
}
