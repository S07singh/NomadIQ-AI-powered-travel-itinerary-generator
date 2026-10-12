import { router } from "expo-router";
import { useState } from "react";
import { View } from "react-native";
import { ApiError, api } from "@/api/client";
import type { AnyOffer } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { OfferCard } from "@/components/offers";
import { Button, Chip, Field, Loading, Notice, Screen, T } from "@/components/ui";
import { holdFare } from "@/lib/hold";
import { isoDaysFromNow } from "@/lib/format";
import { colors } from "@/theme";

const MODES = [
  { id: "trains", label: "Trains" },
  { id: "flights", label: "Flights" },
  { id: "buses", label: "Buses" },
  { id: "hotels", label: "Hotels" },
] as const;
type Mode = (typeof MODES)[number]["id"];

async function toIata(value: string): Promise<string> {
  const v = value.trim();
  if (/^[A-Za-z]{3}$/.test(v)) return v.toUpperCase();
  const hits = await api.airports(v);
  if (!hits.length) throw new ApiError(422, "unknown_airport", `No airport found for "${v}". Try a 3-letter code like BLR.`);
  return hits[0].iata_code;
}

export default function TicketsTab() {
  const { user } = useAuth();
  const [mode, setMode] = useState<Mode>("trains");
  const [origin, setOrigin] = useState(user?.preferences.home_city ?? "");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState(isoDaysFromNow(7));
  const [checkout, setCheckout] = useState(isoDaysFromNow(9));
  const [people, setPeople] = useState("1");
  const [results, setResults] = useState<AnyOffer[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [holding, setHolding] = useState<string | null>(null);
  const currency = user?.preferences.currency ?? "INR";

  const search = async () => {
    setBusy(true);
    setError(null);
    setResults(null);
    try {
      const n = Math.max(Number(people) || 1, 1);
      let res;
      if (mode === "flights") {
        const [o, d] = await Promise.all([toIata(origin), toIata(destination)]);
        res = await api.search("flights", { origin: o, destination: d, departure_date: date, adults: n, currency });
      } else if (mode === "hotels") {
        res = await api.search("hotels", { city: destination, check_in: date, check_out: checkout, adults: n, currency });
      } else {
        res = await api.search(mode, { origin, destination, date, passengers: n, currency });
      }
      setResults([...res.results].sort((a, b) => a.price.amount - b.price.amount));
    } catch (err) {
      const e = err as ApiError;
      setError(e.code === "validation_error" ? "Check the places and dates (YYYY-MM-DD, not in the past)." : e.message);
    } finally {
      setBusy(false);
    }
  };

  const hold = async (offer: AnyOffer) => {
    if (!user) return;
    setHolding(offer.offer_id);
    await holdFare(offer, user);
    setHolding(null);
  };

  return (
    <Screen>
      <T variant="display" style={{ marginTop: 16 }}>Tickets</T>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 16 }}>
        {MODES.map((m) => (
          <Chip key={m.id} label={m.label} on={mode === m.id} onPress={() => { setMode(m.id); setResults(null); }} />
        ))}
      </View>

      <View style={{ gap: 14, marginTop: 20 }}>
        {mode !== "hotels" ? <Field label="From" value={origin} onChangeText={setOrigin} placeholder={mode === "flights" ? "BLR or Bengaluru" : "New Delhi"} /> : null}
        <Field label={mode === "hotels" ? "City" : "To"} value={destination} onChangeText={setDestination} placeholder="Jaipur" />
        <View style={{ flexDirection: "row", gap: 12 }}>
          <Field style={{ flex: 1 }} label={mode === "hotels" ? "Check in" : "Date"} value={date} onChangeText={setDate} placeholder="YYYY-MM-DD" autoCapitalize="none" />
          {mode === "hotels" ? <Field style={{ flex: 1 }} label="Check out" value={checkout} onChangeText={setCheckout} placeholder="YYYY-MM-DD" autoCapitalize="none" /> : null}
          <Field style={{ width: 90 }} label={mode === "hotels" ? "Guests" : "People"} value={people} onChangeText={(v) => setPeople(v.replace(/\D/g, ""))} keyboardType="number-pad" />
        </View>
        <Button title="Search" busy={busy} disabled={!destination.trim() || (mode !== "hotels" && !origin.trim())} onPress={search} />
      </View>

      <View style={{ marginTop: 20 }}>
        {error ? <Notice>{error}</Notice> : null}
        {busy ? <Loading label="Checking live prices" /> : null}
        {results?.length === 0 ? <T style={{ color: colors.slate }}>Nothing available for that day. Try a day either side.</T> : null}
        {results?.map((offer) => (
          <OfferCard
            key={offer.offer_id}
            offer={offer}
            action={<Button title="Select" variant="quiet" busy={holding === offer.offer_id} onPress={() => hold(offer)} style={{ height: 44 }} />}
          />
        ))}
        {results?.length ? (
          <Button title="See all bookings" variant="quiet" onPress={() => router.push("/bookings")} style={{ marginTop: 20 }} />
        ) : null}
      </View>
    </Screen>
  );
}
