import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Alert, View } from "react-native";
import { ApiError, api } from "@/api/client";
import type { Booking } from "@/api/types";
import { OfferCard } from "@/components/offers";
import { Button, Loading, Notice, Screen, T } from "@/components/ui";
import { money } from "@/lib/format";
import { colors } from "@/theme";

const HEADLINES: Record<Booking["status"], string> = {
  awaiting_confirmation: "Review and pay",
  processing: "Confirming",
  confirmed: "You're booked",
  failed: "Booking didn't go through",
  cancelled: "Booking cancelled",
  expired: "Price hold expired",
};

function useCountdown(until?: string | null) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!until) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [until]);
  if (!until) return null;
  const ms = new Date(until).getTime() - now;
  if (ms <= 0) return "expired";
  return `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;
}

export default function BookingScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const left = useCountdown(booking?.status === "awaiting_confirmation" ? booking.confirm_before : null);

  useEffect(() => {
    api.booking(id).then(setBooking).catch(() => setError("This booking doesn't exist or belongs to another account."));
  }, [id]);

  if (!booking) return <Screen edges={["bottom"]}>{error ? <Notice>{error}</Notice> : <Loading label="Loading booking" />}</Screen>;

  const run = async (fn: () => Promise<Booking>) => {
    setBusy(true);
    setError(null);
    try {
      setBooking(await fn());
    } catch (err) {
      const e = err as ApiError;
      if (e.code === "price_mismatch") {
        setBooking(await api.booking(id));
        setError("The price changed. Check the new total before paying.");
      } else setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  // Test-mode token until Razorpay/Stripe's native SDK is wired in; the backend's mock provider accepts it.
  const pay = () => run(() => api.confirmBooking(booking.id, booking.price, "tok_mobile_demo"));
  const cancel = () =>
    Alert.alert(booking.status === "confirmed" ? "Cancel this booking?" : "Release this price hold?", booking.status === "confirmed" ? "Refunds follow the fare rules." : undefined, [
      { text: "Keep", style: "cancel" },
      { text: booking.status === "confirmed" ? "Cancel booking" : "Release", style: "destructive", onPress: () => run(() => api.cancelBooking(booking.id)) },
    ]);

  return (
    <Screen edges={["bottom"]}>
      <T variant="small">{booking.kind[0].toUpperCase() + booking.kind.slice(1)} booking</T>
      <T variant="display">{HEADLINES[booking.status]}</T>

      {booking.status === "confirmed" ? (
        <View style={{ backgroundColor: colors.board, borderRadius: 6, padding: 18, marginTop: 18 }}>
          <T style={{ color: "rgba(255,255,255,0.7)" }}>Booking reference</T>
          <T variant="display" style={{ color: colors.signal, letterSpacing: 1 }}>{booking.provider_reference}</T>
          {booking.tickets.length ? <T style={{ color: "rgba(255,255,255,0.7)", marginTop: 4 }}>Tickets {booking.tickets.join(", ")}</T> : null}
        </View>
      ) : null}

      <View style={{ marginTop: 8 }}>
        <OfferCard offer={booking.offer} />
      </View>

      <T variant="heading" style={{ marginTop: 18 }}>Travelers</T>
      {booking.travelers.map((t, i) => <T key={i}>{t.given_name} {t.family_name}</T>)}
      {booking.contact ? <T variant="small" style={{ marginTop: 4 }}>Tickets go to {booking.contact.email}</T> : null}

      <View style={{ borderLeftWidth: 4, borderLeftColor: colors.signal, paddingLeft: 14, marginTop: 24, gap: 10 }}>
        <View>
          <T variant="small">Total</T>
          <T variant="display">{money(booking.price)}</T>
          {booking.price_changed && booking.original_price ? <T variant="label" style={{ color: colors.brick }}>Was {money(booking.original_price)} when you searched.</T> : null}
        </View>
        {error ? <Notice>{error}</Notice> : null}
        {booking.failure_reason && booking.status !== "awaiting_confirmation" ? <Notice>{booking.failure_reason}</Notice> : null}
        {booking.status === "awaiting_confirmation" ? (
          <>
            {left && left !== "expired" ? <T variant="small">Price held for {left}</T> : null}
            {left === "expired" ? <Notice>The hold has run out. Search again for a fresh price.</Notice> : null}
            <Button title={`Pay ${money(booking.price)} and book`} busy={busy} disabled={left === "expired"} onPress={pay} />
            <Button title="Release hold" variant="quiet" disabled={busy} onPress={cancel} />
            <T variant="small">Test mode: payments are simulated until a payment provider is connected.</T>
          </>
        ) : null}
        {booking.status === "confirmed" ? <Button title="Cancel booking" variant="danger" busy={busy} onPress={cancel} /> : null}
        {booking.status === "expired" || booking.status === "failed" ? <Button title="Search again" onPress={() => router.replace("/tickets")} /> : null}
      </View>
    </Screen>
  );
}
