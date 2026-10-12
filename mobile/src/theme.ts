// Same "route sheet" system as the website: signal yellow is the route, teal is for actions.

export const colors = {
  ink: "#14213D",
  inkSoft: "#2B3A5A",
  paper: "#F3F5F7",
  sheet: "#FFFFFF",
  signal: "#FFC83D",
  signalDeep: "#E5A800",
  platform: "#0F766E",
  platformDeep: "#0B5A54",
  slate: "#5B6573",
  rule: "#D4DAE1",
  brick: "#B83A26",
  board: "#0E1830",
} as const;

export const fonts = {
  regular: "Overpass_400Regular",
  semibold: "Overpass_600SemiBold",
  bold: "Overpass_700Bold",
  heavy: "Overpass_800ExtraBold",
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
export const radius = { sm: 4, md: 6 } as const;
