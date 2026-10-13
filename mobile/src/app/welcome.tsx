import { router } from "expo-router";
import { View } from "react-native";
import Svg, { Circle, Path } from "react-native-svg";
import { Button, Screen, T } from "@/components/ui";
import { colors } from "@/theme";

const STOPS = [
  { y: 20, title: "Bengaluru", note: "06:10 flight" },
  { y: 120, title: "Day 1", note: "Hawa Mahal, Johri Bazaar" },
  { y: 190, title: "Day 2", note: "Amber Fort at sunrise" },
  { y: 270, title: "Home", note: "Overnight train, 2A" },
];
const X = [24, 24, 24, 74];

export default function Welcome() {
  return (
    <Screen edges={["top", "bottom"]}>
      <View style={{ paddingTop: 36 }}>
        <T variant="display" style={{ fontSize: 46, lineHeight: 47 }}>Plan the trip.{"\n"}Book the seats.</T>
        <T style={{ marginTop: 14, fontSize: 18, lineHeight: 26, color: colors.slate }}>
          A day-by-day route with photos, weather and real prices, and the tickets to get there.
        </T>
      </View>

      <View style={{ height: 300, marginTop: 32 }} accessible accessibilityLabel="Example route from Bengaluru to Jaipur">
        <Svg width="100%" height={300} viewBox="0 0 340 300" style={{ position: "absolute" }}>
          <Path d="M24 20 V190 L74 240 V270" stroke={colors.signal} strokeWidth={11} strokeLinecap="round" strokeLinejoin="round" fill="none" />
          {STOPS.map((s, i) => (
            <Circle key={s.title} cx={X[i]} cy={s.y} r={9} fill={i === 0 || i === 3 ? "#fff" : colors.signal} stroke={colors.ink} strokeWidth={3.5} />
          ))}
        </Svg>
        {STOPS.map((s, i) => (
          <View key={s.title} style={{ position: "absolute", top: s.y - 12, left: X[i] + 26 }}>
            <T variant="heading">{s.title}</T>
            <T variant="small">{s.note}</T>
          </View>
        ))}
      </View>

      <View style={{ gap: 12, marginTop: 24 }}>
        <Button title="Create account" onPress={() => router.push("/signup")} />
        <Button title="Sign in" variant="quiet" onPress={() => router.push("/login")} />
      </View>
    </Screen>
  );
}
