import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Alert, Pressable, View } from "react-native";
import { ApiError, api } from "@/api/client";
import type { TravelStyle, Traveler, User } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { Button, Chip, Field, Notice, Rule, Screen, T } from "@/components/ui";
import { colors } from "@/theme";

const STYLES: TravelStyle[] = ["backpacker", "budget", "comfort", "luxury"];
const CURRENCIES = ["INR", "USD", "EUR", "GBP"];

function Preferences({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const [name, setName] = useState(user.name);
  const [homeCity, setHomeCity] = useState(user.preferences.home_city ?? "");
  const [airport, setAirport] = useState(user.preferences.home_airport ?? "");
  const [currency, setCurrency] = useState(user.preferences.currency);
  const [style, setStyle] = useState<TravelStyle>(user.preferences.travel_style);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      onSaved(await api.updateMe({ name, preferences: { home_city: homeCity || null, home_airport: airport ? airport.toUpperCase() : null, currency, travel_style: style } }));
      setSaved(true);
    } catch (err) {
      Alert.alert("Couldn't save", (err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={{ gap: 14 }}>
      <T variant="title" style={{ fontSize: 22 }}>Your defaults</T>
      <Field label="Name" value={name} onChangeText={setName} />
      <View style={{ flexDirection: "row", gap: 12 }}>
        <Field style={{ flex: 1 }} label="Home city" value={homeCity} onChangeText={setHomeCity} placeholder="Bengaluru" />
        <Field style={{ width: 110 }} label="Airport" value={airport} onChangeText={setAirport} placeholder="BLR" maxLength={3} autoCapitalize="characters" />
      </View>
      <T variant="label">Currency</T>
      <View style={{ flexDirection: "row", gap: 8, flexWrap: "wrap" }}>
        {CURRENCIES.map((c) => <Chip key={c} label={c} on={currency === c} onPress={() => setCurrency(c)} />)}
      </View>
      <T variant="label">Travel style</T>
      <View style={{ flexDirection: "row", gap: 8, flexWrap: "wrap" }}>
        {STYLES.map((s) => <Chip key={s} label={s} on={style === s} onPress={() => setStyle(s)} />)}
      </View>
      {saved ? <Notice tone="success">Preferences saved.</Notice> : null}
      <Button title="Save preferences" busy={busy} onPress={save} />
    </View>
  );
}

function Travelers() {
  const [list, setList] = useState<Traveler[]>([]);
  const [first, setFirst] = useState("");
  const [last, setLast] = useState("");
  const [dob, setDob] = useState("");
  const [phone, setPhone] = useState("");
  const [title, setTitle] = useState<"mr" | "ms">("mr");
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      api.travelers().then(setList).catch(() => undefined);
    }, []),
  );

  const add = async () => {
    setError(null);
    try {
      const t = await api.addTraveler({ label: list.length ? first : "Me", title, gender: title === "ms" ? "f" : "m", given_name: first, family_name: last, born_on: dob || null, phone: phone || null });
      setList((cur) => [...cur, t]);
      setFirst("");
      setLast("");
      setDob("");
      setPhone("");
    } catch (err) {
      setError((err as ApiError).code === "validation_error" ? "Check the date of birth (YYYY-MM-DD) and names." : (err as ApiError).message);
    }
  };

  const remove = (t: Traveler) =>
    Alert.alert(`Remove ${t.given_name}?`, undefined, [
      { text: "Keep", style: "cancel" },
      { text: "Remove", style: "destructive", onPress: async () => { await api.deleteTraveler(t.id); setList((cur) => cur.filter((x) => x.id !== t.id)); } },
    ]);

  return (
    <View style={{ gap: 14 }}>
      <T variant="title" style={{ fontSize: 22 }}>Travelers</T>
      <T variant="small">Saved details make booking one tap, and let the assistant hold fares for you by voice.</T>
      {list.map((t) => (
        <View key={t.id} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 6 }}>
          <T variant="label" style={{ fontSize: 16 }}>{t.given_name} {t.family_name}</T>
          <Pressable accessibilityRole="button" onPress={() => remove(t)} hitSlop={10}>
            <T variant="label" style={{ color: colors.brick }}>Remove</T>
          </Pressable>
        </View>
      ))}
      <View style={{ flexDirection: "row", gap: 8 }}>
        <Chip label="Mr" on={title === "mr"} onPress={() => setTitle("mr")} />
        <Chip label="Ms" on={title === "ms"} onPress={() => setTitle("ms")} />
      </View>
      <View style={{ flexDirection: "row", gap: 12 }}>
        <Field style={{ flex: 1 }} label="First name" value={first} onChangeText={setFirst} />
        <Field style={{ flex: 1 }} label="Last name" value={last} onChangeText={setLast} />
      </View>
      <View style={{ flexDirection: "row", gap: 12 }}>
        <Field style={{ flex: 1 }} label="Date of birth" value={dob} onChangeText={setDob} placeholder="1993-04-02" />
        <Field style={{ flex: 1 }} label="Mobile" value={phone} onChangeText={setPhone} placeholder="+91 98765 43210" keyboardType="phone-pad" />
      </View>
      {error ? <Notice>{error}</Notice> : null}
      <Button title="Save traveler" variant="quiet" disabled={!first || !last} onPress={add} />
    </View>
  );
}

export default function ProfileTab() {
  const { user, setUser, logout } = useAuth();
  if (!user) return null;
  return (
    <Screen>
      <T variant="display" style={{ marginTop: 16 }}>{user.name.split(" ")[0]}</T>
      <T variant="small">{user.email}</T>
      <Button title="Bookings" variant="ink" onPress={() => router.push("/bookings")} style={{ marginTop: 20 }} />
      <View style={{ marginVertical: 28 }}><Rule /></View>
      <Preferences user={user} onSaved={setUser} />
      <View style={{ marginVertical: 28 }}><Rule /></View>
      <Travelers />
      <View style={{ marginVertical: 28 }}><Rule /></View>
      <Button title="Sign out" variant="quiet" onPress={logout} />
    </Screen>
  );
}
