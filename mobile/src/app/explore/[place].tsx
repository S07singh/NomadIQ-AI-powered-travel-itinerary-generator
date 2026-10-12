import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Linking, Pressable, ScrollView, View } from "react-native";
import { api } from "@/api/client";
import type { DestinationOverview } from "@/api/types";
import { Button, Loading, Notice, Photo, Screen, T } from "@/components/ui";
import { WEATHER_WORDS, weekday } from "@/lib/format";
import { colors } from "@/theme";

export default function PlaceScreen() {
  const { place } = useLocalSearchParams<{ place: string }>();
  const name = decodeURIComponent(place);
  const [data, setData] = useState<DestinationOverview | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.destination(name).then(setData).catch(() => setError(true));
  }, [name]);

  if (error) return <Screen edges={["bottom"]}><Notice>Couldn&apos;t load {name}. Check your connection.</Notice></Screen>;
  if (!data) return <Screen edges={["bottom"]}><Loading label={`Looking up ${name}`} /></Screen>;

  const where = [data.place?.region, data.place?.country].filter(Boolean).join(", ");

  return (
    <Screen edges={["bottom"]}>
      <T variant="display">{data.place?.name ?? name}</T>
      {where ? <T style={{ color: colors.slate }}>{where}</T> : null}

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 16, marginHorizontal: -16 }} contentContainerStyle={{ gap: 8, paddingHorizontal: 16 }}>
        {data.images.map((img) => <Photo key={img.url} image={img} style={{ width: 280, height: 200 }} />)}
      </ScrollView>

      <View style={{ flexDirection: "row", gap: 10, marginTop: 18 }}>
        <Button title="Plan a trip here" style={{ flex: 1 }} onPress={() => router.push({ pathname: "/trip/new", params: { to: name, days: "4" } })} />
        <Button title="Map" variant="quiet" onPress={() => Linking.openURL(data.maps_url)} />
      </View>

      {data.summary?.summary ? <T style={{ marginTop: 18, fontSize: 17, lineHeight: 26 }}>{data.summary.summary}</T> : null}

      {data.weather.length ? (
        <>
          <T variant="heading" style={{ marginTop: 22 }}>This week&apos;s weather</T>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 10 }} contentContainerStyle={{ gap: 18 }}>
            {data.weather.map((w) => (
              <View key={w.date} style={{ alignItems: "center", minWidth: 56 }}>
                <T variant="label">{weekday(w.date)}</T>
                <T variant="title" style={{ fontSize: 22 }}>{w.temp_max_c != null ? `${Math.round(w.temp_max_c)}°` : ""}</T>
                <T variant="small">{w.temp_min_c != null ? `${Math.round(w.temp_min_c)}°` : ""}</T>
                <T variant="small">{WEATHER_WORDS[w.condition]}</T>
              </View>
            ))}
          </ScrollView>
        </>
      ) : null}

      {data.videos.length ? (
        <View style={{ marginTop: 22, gap: 8 }}>
          <T variant="heading">Videos</T>
          {data.videos.map((v) => (
            <Pressable key={v.url} accessibilityRole="link" onPress={() => Linking.openURL(v.url)}>
              <T variant="label" style={{ color: colors.platform }}>{v.title}</T>
            </Pressable>
          ))}
        </View>
      ) : null}
    </Screen>
  );
}
