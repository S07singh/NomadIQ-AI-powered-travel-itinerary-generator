import { MapPin } from "lucide-react";
import { money, shortDate, weekday, WEATHER_WORDS } from "@/lib/format";
import type { DayPlan, WeatherDay } from "@/lib/types";
import { Photo } from "../photo";

function Weather({ w }: { w: WeatherDay }) {
  const words = WEATHER_WORDS[w.condition];
  return (
    <span className="tabular text-sm text-slate">
      {w.temp_max_c != null ? `${Math.round(w.temp_max_c)}° / ${Math.round(w.temp_min_c ?? 0)}°` : ""}
      {words ? `, ${words.toLowerCase()}` : ""}
      {w.precipitation_probability ? `, ${w.precipitation_probability}% rain` : ""}
    </span>
  );
}

/** The itinerary drawn as a transit line: each day is a station, each activity a stop. */
export function RouteItinerary({ days, currency }: { days: DayPlan[]; currency: string }) {
  return (
    <ol className="relative">
      {days.map((day, di) => (
        <li key={day.day} className="relative pl-12 pb-12 last:pb-2">
          {di < days.length - 1 ? <span aria-hidden className="absolute left-[13px] top-4 bottom-0 w-[8px] bg-signal" /> : null}
          <span aria-hidden className="absolute left-[3px] top-1 w-7 h-7 rounded-full bg-signal border-[5px] border-ink" />
          <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h3 className="heading text-2xl">Day {day.day}</h3>
            {day.date ? <span className="font-semibold text-slate tabular">{weekday(day.date)} {shortDate(day.date)}</span> : null}
            {day.weather ? <Weather w={day.weather} /> : null}
          </header>
          {day.title ? <p className="mt-1 text-lg text-ink-soft">{day.title}</p> : null}

          <ul className="mt-5 space-y-5">
            {day.items.map((item, ii) => (
              <li key={ii} className="relative grid grid-cols-[3.2rem_1fr] sm:grid-cols-[3.6rem_1fr_7rem] gap-x-3">
                <span aria-hidden className="absolute -left-[35px] top-[7px] w-3.5 h-3.5 rounded-full bg-sheet border-[3px] border-ink" />
                <span className="tabular font-bold text-slate pt-0.5">{item.start_time ?? ""}</span>
                <div className="min-w-0">
                  <p className="font-bold text-[1.05rem]">{item.title}</p>
                  {item.description ? <p className="text-slate max-w-[60ch]">{item.description}</p> : null}
                  <div className="mt-1 flex flex-wrap gap-x-4 text-sm">
                    {item.maps_url && item.place_name ? (
                      <a href={item.maps_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-platform hover:underline underline-offset-4">
                        <MapPin size={14} aria-hidden /> {item.place_name}
                      </a>
                    ) : null}
                    {item.estimated_cost ? <span className="text-slate tabular">{money(item.estimated_cost, currency)} each</span> : item.estimated_cost === 0 ? <span className="text-slate">Free</span> : null}
                  </div>
                </div>
                {item.image ? <Photo image={item.image} thumb className="hidden sm:block col-start-3 row-span-2 h-20 rounded-sm" /> : null}
              </li>
            ))}
          </ul>
          {day.notes ? <p className="mt-5 text-sm text-slate border-l-2 border-rule pl-3 max-w-[60ch]">{day.notes}</p> : null}
        </li>
      ))}
    </ol>
  );
}
