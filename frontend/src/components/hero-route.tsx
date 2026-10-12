// Illustrative route for the landing page: a trip drawn the way a metro map draws a line.
// The line draws once on load (the page's single orchestrated motion).

const STOPS = [
  { x: 40, y: 34, title: "Bengaluru", note: "06:10 flight, 2h 35m", filled: false },
  { x: 120, y: 206, title: "Day 1", note: "Hawa Mahal, Johri Bazaar", filled: true },
  { x: 120, y: 296, title: "Day 2", note: "Amber Fort before the crowds", filled: true },
  { x: 200, y: 398, title: "Day 3", note: "Stepwells and a thali lunch", filled: true },
  { x: 200, y: 472, title: "Home", note: "Overnight train, 2A", filled: false },
];

export function HeroRoute() {
  return (
    <figure className="relative w-full max-w-[470px]" aria-label="Example route: Bengaluru to Jaipur in three days">
      <svg viewBox="0 0 470 506" className="w-full max-w-[470px] h-auto" role="img" aria-hidden>
        <path
          d="M40 34 V124 L120 206 V318 L200 398 V472"
          fill="none"
          stroke="#FFC83D"
          strokeWidth="14"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="route-draw"
          style={{ ["--route-length" as string]: 510 }}
        />
        {STOPS.map((s, i) => (
          <g key={s.title} className="station-reveal" style={{ animationDelay: `${0.35 + i * 0.28}s` }}>
            <circle cx={s.x} cy={s.y} r="11" fill={s.filled ? "#FFC83D" : "#fff"} stroke="#14213D" strokeWidth="4" />
            <text x={s.x + 26} y={s.y - 2} className="fill-ink" style={{ font: "800 19px var(--font-overpass)" }}>
              {s.title}
            </text>
            <text x={s.x + 26} y={s.y + 19} className="fill-slate" style={{ font: "400 15px var(--font-overpass)" }}>
              {s.note}
            </text>
          </g>
        ))}
      </svg>
    </figure>
  );
}
