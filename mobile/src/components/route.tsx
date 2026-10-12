import { Linking, Pressable, StyleSheet, View } from "react-native";
import type { DayPlan, TripProgress } from "@/api/types";
import { WEATHER_WORDS, money, shortDate, weekday } from "@/lib/format";
import { colors, fonts, radius } from "@/theme";
import { Photo, Station, T } from "./ui";

/** Itinerary as a transit line: days are stations, activities are stops. */
export function RouteItinerary({ days, currency }: { days: DayPlan[]; currency: string }) {
  return (
    <View>
      {days.map((day, di) => (
        <View key={day.day} style={styles.day}>
          {di < days.length - 1 ? <View style={styles.line} /> : null}
          <View style={styles.dayStation}>
            <Station size={26} />
          </View>
          <View style={{ flexDirection: "row", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <T variant="title" style={{ fontSize: 24 }}>Day {day.day}</T>
            {day.date ? <T variant="label" style={{ color: colors.slate }}>{weekday(day.date)} {shortDate(day.date)}</T> : null}
          </View>
          {day.weather ? (
            <T variant="small">
              {day.weather.temp_max_c != null ? `${Math.round(day.weather.temp_max_c)}° / ${Math.round(day.weather.temp_min_c ?? 0)}°` : ""}
              {WEATHER_WORDS[day.weather.condition] ? `, ${WEATHER_WORDS[day.weather.condition].toLowerCase()}` : ""}
            </T>
          ) : null}
          {day.title ? <T style={{ marginTop: 2, color: colors.inkSoft }}>{day.title}</T> : null}

          <View style={{ marginTop: 14, gap: 16 }}>
            {day.items.map((item, ii) => (
              <View key={ii} style={styles.stop}>
                <View style={styles.stopDot}>
                  <Station filled={false} size={13} />
                </View>
                <T variant="label" style={{ width: 48, color: colors.slate }}>{item.start_time ?? ""}</T>
                <View style={{ flex: 1 }}>
                  <T variant="label" style={{ fontSize: 16 }}>{item.title}</T>
                  {item.description ? <T variant="small">{item.description}</T> : null}
                  <View style={{ flexDirection: "row", gap: 12, flexWrap: "wrap", marginTop: 2 }}>
                    {item.maps_url && item.place_name ? (
                      <Pressable accessibilityRole="link" onPress={() => Linking.openURL(item.maps_url!)} hitSlop={8}>
                        <T variant="small" style={{ color: colors.platform, fontFamily: fonts.bold }}>{item.place_name}</T>
                      </Pressable>
                    ) : null}
                    {item.estimated_cost ? <T variant="small">{money(item.estimated_cost, currency)} each</T> : item.estimated_cost === 0 ? <T variant="small">Free</T> : null}
                  </View>
                </View>
                {item.image ? <Photo image={item.image} thumb style={{ width: 64, height: 52 }} /> : null}
              </View>
            ))}
          </View>
          {day.notes ? <T variant="small" style={styles.note}>{day.notes}</T> : null}
        </View>
      ))}
    </View>
  );
}

const STEPS = [
  { step: "research", label: "Sights, stays and food" },
  { step: "itinerary", label: "Day-by-day route" },
  { step: "enrich", label: "Photos, maps, weather" },
  { step: "done", label: "Ready to view" },
];
const ORDER = ["queued", "research", "itinerary", "enrich", "done"];

/** Generation progress as a station departure board. */
export function DepartureBoard({ progress, destination }: { progress: TripProgress; destination: string }) {
  const current = ORDER.indexOf(progress.step || "queued");
  return (
    <View style={styles.board} accessibilityLiveRegion="polite">
      <View style={styles.boardHead}>
        <T variant="heading" style={{ color: colors.signal, flex: 1 }}>Now planning: {destination}</T>
        <T style={{ color: "rgba(255,255,255,0.6)" }}>{progress.percent}%</T>
      </View>
      {STEPS.map((row) => {
        const idx = ORDER.indexOf(row.step);
        const state = idx < current ? "Done" : idx === current ? "Now" : "Next";
        return (
          <View key={row.step} style={styles.boardRow}>
            <T style={{ color: "#fff", fontFamily: fonts.semibold, flex: 1 }}>{row.label}</T>
            <View style={[styles.pill, state === "Done" && { backgroundColor: colors.platform }, state === "Now" && { backgroundColor: colors.signal }]}>
              <T variant="label" style={{ color: state === "Now" ? colors.ink : state === "Done" ? "#fff" : "rgba(255,255,255,0.45)" }}>{state}</T>
            </View>
          </View>
        );
      })}
      <T style={{ color: "rgba(255,255,255,0.7)", padding: 16 }}>{progress.message || "Queued"}</T>
    </View>
  );
}

const styles = StyleSheet.create({
  day: { paddingLeft: 40, paddingBottom: 36 },
  line: { position: "absolute", left: 10, top: 14, bottom: 0, width: 7, backgroundColor: colors.signal },
  dayStation: { position: "absolute", left: 0, top: 2 },
  stop: { flexDirection: "row", gap: 8, alignItems: "flex-start" },
  stopDot: { position: "absolute", left: -33, top: 3 },
  note: { marginTop: 14, borderLeftWidth: 2, borderLeftColor: colors.rule, paddingLeft: 10 },
  board: { backgroundColor: colors.board, borderRadius: radius.md, overflow: "hidden" },
  boardHead: { flexDirection: "row", alignItems: "center", padding: 16, borderBottomWidth: 1, borderBottomColor: "rgba(255,255,255,0.15)" },
  boardRow: { flexDirection: "row", alignItems: "center", paddingHorizontal: 16, paddingVertical: 13, borderBottomWidth: 1, borderBottomColor: "rgba(255,255,255,0.1)" },
  pill: { minWidth: 58, alignItems: "center", paddingHorizontal: 8, paddingVertical: 3, borderRadius: 3 },
});
