import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { TextInput, View } from "react-native";
import { ApiError, api } from "@/api/client";
import type { TravelStyle, TripPace } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { Button, Chip, Field, Notice, Screen, T } from "@/components/ui";
import { isoDaysFromNow } from "@/lib/format";
import { colors, fonts, radius } from "@/theme";

const VIBES = ["culture", "food", "nature", "adventure", "relaxation", "nightlife", "shopping", "spiritual", "family"];
const WHEN = [
  { label: "This weekend", days: ((6 - new Date().getDay() + 7) % 7) || 7 },
  { label: "In two weeks", days: 14 },
  { label: "Next month", days: 30 },
];

export default function NewTrip() {
  const { user } = useAuth();
  const params = useLocalSearchParams<{ to?: string; days?: string; from?: string; budget?: string; currency?: string }>();
  const [destination, setDestination] = useState(params.to ?? "");
  const [origin, setOrigin] = useState(params.from ?? user?.preferences.home_city ?? "");
  const [days, setDays] = useState(params.days ?? "4");
  const [start, setStart] = useState("");
  const [adults, setAdults] = useState("2");
  const [budget, setBudget] = useState(params.budget ?? "");
  const currency = params.currency ?? user?.preferences.currency ?? "INR";
  const [style, setStyle] = useState<TravelStyle>(user?.preferences.travel_style ?? "comfort");
  const [pace, setPace] = useState<TripPace>("moderate");
  const [vibes, setVibes] = useState<string[]>(["culture", "food"]);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const toggle = (v: string) => setVibes((cur) => (cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v].slice(0, 8)));

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const trip = await api.createTrip({
        destination: destination.trim(),
        origin: origin.trim() || null,
        start_date: start || null,
        duration_days: Number(days) || 3,
        travelers: { adults: Number(adults) || 1, children: 0, infants: 0 },
        budget: budget ? { amount: Number(budget), currency } : null,
        travel_style: style,
        pace,
        vibes,
        additional_info: notes,
      });
      router.replace(`/trip/${trip.id}`);
    } catch (err) {
      setError((err as ApiError).code === "validation_error" ? "Check the dates (YYYY-MM-DD, not in the past) and number of days (1 to 30)." : (err as ApiError).message);
      setBusy(false);
    }
  };

  return (
    <Screen edges={["bottom"]}>
      <View style={{ gap: 16, marginTop: 8 }}>
        <Field label="Destination" value={destination} onChangeText={setDestination} placeholder="Jaipur, India" />
        <Field label="Starting from" value={origin} onChangeText={setOrigin} placeholder="Bengaluru" />
        <View style={{ flexDirection: "row", gap: 12 }}>
          <Field style={{ flex: 1 }} label="Days" value={days} onChangeText={(v) => setDays(v.replace(/\D/g, ""))} keyboardType="number-pad" />
          <Field style={{ flex: 1 }} label="Adults" value={adults} onChangeText={(v) => setAdults(v.replace(/\D/g, ""))} keyboardType="number-pad" />
          <Field style={{ flex: 1.4 }} label={`Budget, ${currency}`} value={budget} onChangeText={(v) => setBudget(v.replace(/\D/g, ""))} keyboardType="number-pad" placeholder="40000" />
        </View>

        <T variant="label">First day</T>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {WHEN.map((w) => {
            const iso = isoDaysFromNow(w.days);
            return <Chip key={w.label} label={w.label} on={start === iso} onPress={() => setStart(start === iso ? "" : iso)} />;
          })}
        </View>
        <Field label="Or a date" value={start} onChangeText={setStart} placeholder="YYYY-MM-DD, empty if open" autoCapitalize="none" />

        <T variant="label">How you like to travel</T>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {(["backpacker", "budget", "comfort", "luxury"] as TravelStyle[]).map((s) => <Chip key={s} label={s} on={style === s} onPress={() => setStyle(s)} />)}
        </View>
        <T variant="label">Pace</T>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {(["relaxed", "moderate", "packed"] as TripPace[]).map((p) => <Chip key={p} label={p} on={pace === p} onPress={() => setPace(p)} />)}
        </View>
        <T variant="label">What you&apos;re into</T>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {VIBES.map((v) => <Chip key={v} label={v} on={vibes.includes(v)} onPress={() => toggle(v)} />)}
        </View>

        <T variant="label">Anything else</T>
        <TextInput
          multiline
          value={notes}
          onChangeText={setNotes}
          placeholder="Vegetarian, a birthday dinner, a bad knee"
          placeholderTextColor="#9AA3AE"
          accessibilityLabel="Anything else"
          style={{ minHeight: 90, borderWidth: 2, borderColor: colors.rule, borderRadius: radius.md, backgroundColor: colors.sheet, padding: 12, fontFamily: fonts.regular, fontSize: 16, color: colors.ink, textAlignVertical: "top" }}
        />
        {error ? <Notice>{error}</Notice> : null}
        <Button title="Draw my route" busy={busy} disabled={destination.trim().length < 2} onPress={create} />
        <T variant="small">Planning runs in the background. You can leave this screen and come back.</T>
      </View>
    </Screen>
  );
}
