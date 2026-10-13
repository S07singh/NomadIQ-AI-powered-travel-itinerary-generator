import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { FlatList, Pressable, RefreshControl, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { api } from "@/api/client";
import type { TripStatus, TripSummary } from "@/api/types";
import { Button, Loading, Notice, Photo, T } from "@/components/ui";
import { dateRange } from "@/lib/format";
import { colors } from "@/theme";

const STATUS: Record<TripStatus, string> = { draft: "Not planned", queued: "Planning", generating: "Planning", ready: "", failed: "Needs another try" };

export default function TripsTab() {
  const [trips, setTrips] = useState<TripSummary[] | null>(null);
  const [error, setError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      setTrips((await api.trips()).items);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.paper }}>
      <FlatList
        data={trips ?? []}
        keyExtractor={(t) => t.id}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}
        ListHeaderComponent={
          <View style={{ paddingTop: 16, paddingBottom: 12, flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
            <T variant="display">Trips</T>
            <Button title="New trip" variant="quiet" onPress={() => router.push("/trip/new")} style={{ height: 42 }} />
          </View>
        }
        ListEmptyComponent={
          error ? (
            <Notice>Couldn&apos;t load your trips. Pull down to try again.</Notice>
          ) : trips === null ? (
            <Loading />
          ) : (
            <View style={{ borderLeftWidth: 4, borderLeftColor: colors.signal, paddingLeft: 16, marginTop: 12 }}>
              <T variant="heading">No trips yet</T>
              <T variant="small" style={{ marginTop: 4 }}>Start with a destination and a number of days. You get a route you can change by talking to it.</T>
            </View>
          )
        }
        ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: colors.rule }} />}
        renderItem={({ item }) => (
          <Pressable accessibilityRole="link" onPress={() => router.push(`/trip/${item.id}`)} style={{ flexDirection: "row", gap: 14, paddingVertical: 14, alignItems: "center" }}>
            <Photo image={item.cover_image} thumb style={{ width: 84, height: 64 }} />
            <View style={{ flex: 1 }}>
              <T variant="heading">{item.destination.split(",")[0]}</T>
              <T variant="small">{dateRange(item.start_date, item.end_date, item.duration_days)}, {item.duration_days} days</T>
              {STATUS[item.status] ? <T variant="label" style={{ color: item.status === "failed" ? colors.brick : colors.slate, marginTop: 2 }}>{STATUS[item.status]}</T> : null}
            </View>
          </Pressable>
        )}
      />
    </SafeAreaView>
  );
}
