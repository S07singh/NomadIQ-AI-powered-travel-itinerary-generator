import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, TextInput, View } from "react-native";
import { api } from "@/api/client";
import type { MediaImage } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { Button, Photo, Screen, T } from "@/components/ui";
import { currencySymbol } from "@/lib/format";
import { colors, fonts } from "@/theme";

const PLACES = [
  { name: "Jaipur", query: "Hawa Mahal Jaipur", note: "Nov to Feb, 4 days" },
  { name: "Hampi", query: "Hampi Virupaksha Temple", note: "Winter, 3 days" },
  { name: "Munnar", query: "Munnar tea plantations", note: "Sep to Mar, 3 days" },
  { name: "Kyoto", query: "Fushimi Inari Kyoto", note: "Spring or autumn" },
  { name: "Lisbon", query: "Alfama Lisbon", note: "Almost all year" },
];

function Blank({ value, onChange, placeholder, width, numeric, label }: { value: string; onChange: (v: string) => void; placeholder: string; width: number; numeric?: boolean; label: string }) {
  return (
    <TextInput
      accessibilityLabel={label}
      value={value}
      onChangeText={onChange}
      placeholder={placeholder}
      placeholderTextColor="#A4ACB6"
      keyboardType={numeric ? "number-pad" : "default"}
      style={[styles.blank, { width }]}
    />
  );
}

function PlaceCard({ name, query, note }: (typeof PLACES)[number]) {
  const [image, setImage] = useState<MediaImage | null>(null);
  useEffect(() => {
    api.images(query, 1).then((r) => setImage(r[0] ?? null)).catch(() => undefined);
  }, [query]);
  return (
    <Pressable accessibilityRole="link" onPress={() => router.push(`/explore/${encodeURIComponent(name)}`)} style={{ width: 200 }}>
      <Photo image={image} thumb style={{ height: 150 }} />
      <T variant="heading" style={{ marginTop: 8 }}>{name}</T>
      <T variant="small">{note}</T>
    </Pressable>
  );
}

export default function PlanTab() {
  const { user } = useAuth();
  const currency = user?.preferences.currency ?? "INR";
  const [to, setTo] = useState("");
  const [days, setDays] = useState("4");
  const [from, setFrom] = useState(user?.preferences.home_city ?? "");
  const [budget, setBudget] = useState("");

  const go = () =>
    router.push({ pathname: "/trip/new", params: { to: to.trim(), days, from: from.trim(), budget, currency } });

  return (
    <Screen>
      <T variant="label" style={{ color: colors.slate, marginTop: 16 }}>Hi {user?.name.split(" ")[0]}</T>
      <T variant="display" style={{ marginTop: 4 }}>Where to next?</T>

      <View style={styles.sentence}>
        <T style={styles.words}>I&apos;m going to</T>
        <Blank label="Destination" value={to} onChange={setTo} placeholder="Jaipur" width={150} />
        <T style={styles.words}>for</T>
        <Blank label="Number of days" value={days} onChange={(v) => setDays(v.replace(/\D/g, "").slice(0, 2))} placeholder="4" width={36} numeric />
        <T style={styles.words}>days from</T>
        <Blank label="Starting city" value={from} onChange={setFrom} placeholder="Bengaluru" width={160} />
        <T style={styles.words}>with about {currencySymbol(currency)}</T>
        <Blank label="Budget" value={budget} onChange={(v) => setBudget(v.replace(/\D/g, ""))} placeholder="40000" width={110} numeric />
        <T style={styles.words}>to spend.</T>
      </View>
      <Button title="Draw my route" disabled={to.trim().length < 2} onPress={go} style={{ marginTop: 24 }} />

      <T variant="title" style={{ marginTop: 40, fontSize: 24 }}>Where people are going</T>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 14, paddingTop: 14, paddingRight: 16 }} style={{ marginRight: -16 }}>
        {PLACES.map((p) => (
          <PlaceCard key={p.name} {...p} />
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  sentence: { flexDirection: "row", flexWrap: "wrap", alignItems: "flex-end", marginTop: 28, rowGap: 10, columnGap: 8 },
  words: { fontFamily: fonts.semibold, fontSize: 24, lineHeight: 38 },
  blank: {
    fontFamily: fonts.bold,
    fontSize: 24,
    color: colors.ink,
    borderBottomWidth: 3,
    borderBottomColor: colors.ink,
    paddingVertical: 2,
    paddingHorizontal: 2,
    height: 42,
  },
});
