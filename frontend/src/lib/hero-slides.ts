// Shared between the server (page.tsx, resolves the photos) and the client (hero.tsx, animates
// them) — kept in a plain module so neither side crosses the "use client" boundary for just data.
export const HERO_SLIDES = [
  { query: "Hawa Mahal Jaipur", credit: "Jaipur, India" },
  { query: "Fushimi Inari Taisha Kyoto", credit: "Kyoto, Japan" },
  { query: "Oia Santorini", credit: "Santorini, Greece" },
  { query: "Pangong Lake Ladakh", credit: "Ladakh, India" },
  { query: "Hampi Virupaksha Temple", credit: "Hampi, India" },
] as const;
