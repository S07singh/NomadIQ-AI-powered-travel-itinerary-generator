import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, View } from "react-native";
import { api } from "@/api/client";
import type { BookingStatus, BookingSummary } from "@/api/types";
import { Button, Loading, Notice, Screen, T } from "@/components/ui";
import { money, shortDate } from "@/lib/format";
import { colors } from "@/theme";

const STATUS: Record<BookingStatus, { label: string; color: string }> = {
  awaiting_confirmation: { label: "Waiting for payment", color: colors.ink },
  processing: { label: "Confirming", color: colors.slate },
  confirmed: { label: "Confirmed", color: colors.platformDeep },
  failed: { label: "Failed, refunded", color: colors.brick },
  cancelled: { label: "Cancelled", color: colors.slate },
  expired: { label: "Hold expired", color: colors.slate },
};

export default function BookingsScreen() {
  const [items, setItems] = useState<BookingSummary[] | null>(null);
  const [error, setError] = useState(false);

  useFocusEffect(
    useCallback(() => {
      api.bookings().then((p) => setItems(p.items)).catch(() => setError(true));
    }, []),
  );

  return (
    <Screen edges={["bottom"]}>
      {error ? <Notice>Couldn&apos;t load bookings. Try again in a moment.</Notice> : null}
      {!items && !error ? <Loading /> : null}
      {items?.length === 0 ? (
        <View style={{ gap: 12 }}>
          <T variant="heading">Nothing booked yet</T>
          <T variant="small">Search trains, flights, buses or hotels and hold a fare. It shows up here.</T>
          <Button title="Find tickets" onPress={() => router.replace("/tickets")} />
        </View>
      ) : null}
      {items?.map((b) => (
        <Pressable key={b.id} accessibilityRole="link" onPress={() => router.push(`/booking/${b.id}`)} style={{ paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: colors.rule }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 12 }}>
            <T variant="heading" style={{ flex: 1 }}>{b.title}</T>
            <T variant="heading">{money(b.price)}</T>
          </View>
          <T variant="small">{b.kind[0].toUpperCase() + b.kind.slice(1)}, made {shortDate(b.created_at)}{b.provider_reference ? `, ref ${b.provider_reference}` : ""}</T>
          <T variant="label" style={{ color: STATUS[b.status].color, marginTop: 2 }}>{STATUS[b.status].label}</T>
        </Pressable>
      ))}
    </Screen>
  );
}
