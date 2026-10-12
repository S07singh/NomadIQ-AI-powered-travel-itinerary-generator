// Tab glyphs drawn in the route-map language (stations, lines, tickets) instead of a stock icon set.
import type { ColorValue } from "react-native";
import Svg, { Circle, Line, Path, Rect } from "react-native-svg";

type P = { color: ColorValue; size?: number };

export function PlanIcon({ color, size = 26 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 26 26" fill="none">
      <Path d="M6 4 V11 L18 19 V23" stroke={color} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
      <Circle cx={6} cy={5} r={3} fill="#fff" stroke={color} strokeWidth={2.4} />
      <Circle cx={18} cy={21} r={3} fill={color} stroke={color} strokeWidth={2.4} />
    </Svg>
  );
}

export function TripsIcon({ color, size = 26 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 26 26" fill="none">
      <Line x1={7} y1={4} x2={7} y2={22} stroke={color} strokeWidth={3} strokeLinecap="round" />
      {[6, 13, 20].map((y) => (
        <Circle key={y} cx={7} cy={y} r={2.8} fill="#fff" stroke={color} strokeWidth={2.2} />
      ))}
      {[6, 13, 20].map((y) => (
        <Line key={`l${y}`} x1={13} y1={y} x2={22} y2={y} stroke={color} strokeWidth={2.4} strokeLinecap="round" />
      ))}
    </Svg>
  );
}

export function TalkIcon({ color, size = 26 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 26 26" fill="none">
      <Rect x={9} y={3} width={8} height={13} rx={4} stroke={color} strokeWidth={2.4} />
      <Path d="M5 12 a8 8 0 0 0 16 0 M13 20 V24" stroke={color} strokeWidth={2.4} strokeLinecap="round" />
    </Svg>
  );
}

export function TicketIcon({ color, size = 26 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 26 26" fill="none">
      <Path d="M3 8 V6 H23 V10 a3 3 0 0 0 0 6 V20 H3 V16 a3 3 0 0 0 0 -6 Z" stroke={color} strokeWidth={2.4} strokeLinejoin="round" />
      <Line x1={16} y1={8} x2={16} y2={18} stroke={color} strokeWidth={2} strokeDasharray="2 2.5" />
    </Svg>
  );
}

export function YouIcon({ color, size = 26 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 26 26" fill="none">
      <Circle cx={13} cy={9} r={4.5} stroke={color} strokeWidth={2.4} />
      <Path d="M4.5 23 a8.5 8 0 0 1 17 0" stroke={color} strokeWidth={2.4} strokeLinecap="round" />
    </Svg>
  );
}
