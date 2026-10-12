import { Stack, router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Alert, Linking, Pressable, Share, View } from "react-native";
import { ApiError, api } from "@/api/client";
import type { Trip, TripProgress } from "@/api/types";
import { DepartureBoard, RouteItinerary } from "@/components/route";
import { Button, Chip, Field, Loading, Notice, Photo, Rule, Screen, T } from "@/components/ui";
import { dateRange, money } from "@/lib/format";
import { colors, fonts } from "@/theme";

type Section = "route" | "stays" | "food" | "budget";
const SECTIONS: { id: Section; label: string }[] = [
  { id: "route", label: "Route" },
  { id: "stays", label: "Stays" },
  { id: "food", label: "Food" },
  { id: "budget", label: "Budget" },
];
const BUSY = new Set(["queued", "generating"]);
const LINE_LABELS = { accommodation: "Stays", food: "Food", activities: "Things to do", local_transport: "Getting around", misc: "Buffer" } as const;

export default function TripScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [progress, setProgress] = useState<TripProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<Section>("route");
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState<string | null>(null);
  const [chatting, setChatting] = useState(false);

  useEffect(() => {
    api
      .trip(id)
      .then((t) => {
        setTrip(t);
        setProgress(t.progress);
      })
      .catch(() => setError("This trip doesn't exist or belongs to another account."));
  }, [id]);

  // Mobile polls the lightweight /status endpoint (streaming fetch isn't reliable on React Native).
  const generating = !!progress && BUSY.has(progress.status);
  useEffect(() => {
    if (!generating) return;
    let alive = true;
    const tick = async () => {
      try {
        const p = await api.tripStatus(id);
        if (!alive) return;
        setProgress(p);
        if (p.status === "ready" || p.status === "failed") setTrip(await api.trip(id));
      } catch {
        /* keep polling */
      }
    };
    const timer = setInterval(tick, 1500);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [generating, id]);

  if (error) return <Screen edges={["bottom"]}><Notice>{error}</Notice></Screen>;
  if (!trip || !progress) return <Screen edges={["bottom"]}><Loading label="Loading trip" /></Screen>;

  const plan = trip.plan;
  const currency = trip.budget?.currency ?? "USD";
  const city = trip.destination.split(",")[0];

  const regenerate = async () => {
    const t = await api.regenerate(trip.id);
    setTrip(t);
    setProgress(t.progress);
  };
  const share = async () => {
    const res = await api.shareTrip(trip.id);
    await Share.share({ message: `My ${city} trip on NomadIQ: ${res.share_url}` });
  };
  const remove = () =>
    Alert.alert("Delete this trip?", "This can't be undone.", [
      { text: "Keep", style: "cancel" },
      { text: "Delete", style: "destructive", onPress: async () => { await api.deleteTrip(trip.id); router.back(); } },
    ]);
  const ask = async () => {
    if (!message.trim()) return;
    setChatting(true);
    try {
      const res = await api.tripChat(trip.id, message.trim());
      setReply(res.reply.content);
      setMessage("");
      if (res.plan_updated) setTrip(res.trip);
    } catch (err) {
      setReply((err as ApiError).message);
    } finally {
      setChatting(false);
    }
  };

  return (
    <Screen edges={["bottom"]}>
      <Stack.Screen options={{ headerTitle: "" }} />
      <T variant="display">{city}</T>
      <T style={{ color: colors.slate, marginTop: 4 }}>
        {dateRange(trip.start_date, trip.end_date, trip.duration_days)}, {trip.duration_days} days, {trip.travelers.adults + trip.travelers.children} travelers
      </T>

      {generating ? <View style={{ marginTop: 20 }}><DepartureBoard progress={progress} destination={city} /></View> : null}

      {progress.status === "failed" ? (
        <View style={{ gap: 12, marginTop: 20 }}>
          <Notice>{trip.error === "interrupted" ? "Planning was interrupted." : trip.error || "Planning failed."} Your inputs are saved.</Notice>
          <Button title="Try planning again" onPress={regenerate} />
        </View>
      ) : null}
      {progress.status === "draft" ? <Button title="Draw the route" onPress={regenerate} style={{ marginTop: 20 }} /> : null}

      {trip.status === "ready" && plan ? (
        <>
          <Photo image={plan.cover_image} style={{ height: 220, marginTop: 18 }} />
          {plan.summary ? <T style={{ marginTop: 14, fontSize: 17, lineHeight: 25 }}>{plan.summary}</T> : null}

          <View style={{ flexDirection: "row", gap: 8, marginTop: 20, flexWrap: "wrap" }}>
            {SECTIONS.map((s) => <Chip key={s.id} label={s.label} on={section === s.id} onPress={() => setSection(s.id)} />)}
          </View>
          <View style={{ marginTop: 22 }}>
            {section === "route" ? <RouteItinerary days={plan.days} currency={currency} /> : null}

            {section === "stays"
              ? plan.hotels.map((h) => (
                  <View key={h.name} style={{ paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: colors.rule }}>
                    <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 10 }}>
                      <T variant="heading" style={{ flex: 1 }}>{h.name}</T>
                      {h.price_per_night ? <T variant="heading">{money(h.price_per_night, currency)}</T> : null}
                    </View>
                    <T variant="small">{[h.area, h.rating ? `${h.rating.toFixed(1)} rating` : null].filter(Boolean).join(", ")}</T>
                    {h.why ? <T style={{ marginTop: 4 }}>{h.why}</T> : null}
                    <View style={{ flexDirection: "row", gap: 18, marginTop: 6 }}>
                      <Pressable accessibilityRole="link" onPress={() => router.push("/tickets")}><T variant="label" style={{ color: colors.platform }}>Check live prices</T></Pressable>
                      {h.maps_url ? <Pressable accessibilityRole="link" onPress={() => Linking.openURL(h.maps_url!)}><T variant="label" style={{ color: colors.platform }}>Map</T></Pressable> : null}
                    </View>
                  </View>
                ))
              : null}

            {section === "food" ? (
              <View style={{ gap: 14 }}>
                {plan.local_dishes.length ? <T>Eat while you&apos;re there: {plan.local_dishes.join(", ")}.</T> : null}
                {plan.restaurants.map((r) => (
                  <View key={r.name} style={{ borderTopWidth: 2, borderTopColor: colors.ink, paddingTop: 10 }}>
                    <T variant="heading">{r.name}</T>
                    <T variant="small">{[r.cuisine, r.area, r.avg_cost_per_person ? `about ${money(r.avg_cost_per_person, currency)} a person` : null].filter(Boolean).join(", ")}</T>
                    {r.must_try.length ? <T style={{ marginTop: 2 }}>Order: {r.must_try.join(", ")}</T> : null}
                  </View>
                ))}
              </View>
            ) : null}

            {section === "budget" && plan.budget ? (
              <View>
                <T variant="small">Estimated total</T>
                <T variant="display">{money(plan.budget.total, plan.budget.currency)}</T>
                <T variant="small">{money(plan.budget.per_person, plan.budget.currency)} a person, {money(plan.budget.per_day, plan.budget.currency)} a day</T>
                {plan.budget.budget_limit ? (
                  <T variant="label" style={{ marginTop: 8, color: plan.budget.within_budget ? colors.platformDeep : colors.brick }}>
                    {plan.budget.within_budget ? "Within" : "Over"} your {money(plan.budget.budget_limit, plan.budget.currency)} budget.
                  </T>
                ) : null}
                <View style={{ marginTop: 14 }}>
                  {plan.budget.lines.map((l) => (
                    <View key={l.category} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.rule }}>
                      <T variant="label">{LINE_LABELS[l.category]}</T>
                      <T variant="label">{money(l.amount, plan.budget!.currency)}</T>
                    </View>
                  ))}
                </View>
                {plan.budget.tips.map((t) => <T key={t} variant="small" style={{ marginTop: 6 }}>{t}</T>)}
              </View>
            ) : null}
          </View>

          <View style={{ marginVertical: 24 }}><Rule /></View>
          <T variant="title" style={{ fontSize: 22 }}>Change something</T>
          <T variant="small" style={{ marginBottom: 10 }}>Ask in plain words. The route redraws when the plan changes.</T>
          <Field label="Request" value={message} onChangeText={setMessage} placeholder="Add a sunset spot on day 3" onSubmitEditing={ask} returnKeyType="send" />
          <Button title="Update the route" busy={chatting} disabled={!message.trim()} onPress={ask} style={{ marginTop: 10 }} />
          {reply ? <T style={{ marginTop: 12, borderLeftWidth: 4, borderLeftColor: colors.ink, paddingLeft: 10, fontFamily: fonts.semibold }}>{reply}</T> : null}

          {plan.videos.length ? (
            <View style={{ marginTop: 24, gap: 8 }}>
              <T variant="heading">Watch before you go</T>
              {plan.videos.map((v) => (
                <Pressable key={v.url} accessibilityRole="link" onPress={() => Linking.openURL(v.url)}>
                  <T variant="label" style={{ color: colors.platform }}>{v.title}</T>
                </Pressable>
              ))}
            </View>
          ) : null}

          <View style={{ flexDirection: "row", gap: 10, marginTop: 28 }}>
            <Button title="Share" variant="quiet" onPress={share} style={{ flex: 1 }} />
            <Button title="Plan again" variant="quiet" onPress={regenerate} style={{ flex: 1 }} />
          </View>
          <Button title="Delete trip" variant="danger" onPress={remove} style={{ marginTop: 10 }} />
        </>
      ) : null}
    </Screen>
  );
}
