import { useState } from "react";
import { Linking, Pressable, View } from "react-native";
import type { AnyOffer, Trip, User } from "@/api/types";
import { holdFare } from "@/lib/hold";
import { shortDate, weekday } from "@/lib/format";
import { colors } from "@/theme";
import { OfferCard } from "./offers";
import { Button, Photo, T } from "./ui";

export function hostname(url: string): string {
  const m = url.match(/^https?:\/\/(?:www\.)?([^/]+)/);
  return m ? m[1] : url;
}

export function TextLink({ label, url }: { label: string; url: string }) {
  return (
    <Pressable accessibilityRole="link" onPress={() => Linking.openURL(url)} hitSlop={8}>
      <T variant="label" style={{ color: colors.platform }}>{label}</T>
    </Pressable>
  );
}

/** Select = hold the fare in-app; fares we can't sell (Google Flights prices) open the source site. */
export function OfferAction({ offer, user, title = "Select" }: { offer: AnyOffer; user: User | null; title?: string }) {
  const [busy, setBusy] = useState(false);
  if (!offer.bookable) {
    return offer.deep_link ? (
      <Button title={offer.provider === "google_flights" ? "Book on Google" : "Book on site"} variant="quiet" onPress={() => Linking.openURL(offer.deep_link!)} style={{ height: 44 }} />
    ) : null;
  }
  return (
    <Button
      title={title}
      variant="quiet"
      busy={busy}
      style={{ height: 44 }}
      onPress={async () => {
        if (!user) return;
        setBusy(true);
        await holdFare(offer, user);
        setBusy(false);
      }}
    />
  );
}

export function SightsSection({ trip }: { trip: Trip }) {
  const plan = trip.plan!;
  return (
    <View style={{ gap: 22 }}>
      {plan.attractions.map((a) => (
        <View key={a.name}>
          <Photo image={a.images[0]} style={{ height: 190 }} />
          <T variant="heading" style={{ marginTop: 8 }}>{a.name}</T>
          {a.description ? <T variant="small">{a.description}</T> : null}
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 16, marginTop: 6 }}>
            {a.maps_url ? <TextLink label="Map" url={a.maps_url} /> : null}
            {a.videos[0] ? <TextLink label="Videos" url={a.videos[0].url} /> : null}
            {a.source_url ? <TextLink label={`Read more on ${hostname(a.source_url)}`} url={a.source_url} /> : null}
          </View>
        </View>
      ))}
    </View>
  );
}

export function FlightsSection({ trip, user }: { trip: Trip; user: User | null }) {
  const f = trip.plan?.flights;
  if (!f) return null;
  const leg = (title: string, date: string | null | undefined, offers: AnyOffer[]) =>
    offers.length ? (
      <View style={{ marginBottom: 18 }}>
        <T variant="title" style={{ fontSize: 20 }}>
          {title}
          {date ? <T variant="label" style={{ color: colors.slate }}>{`  ${weekday(date)} ${shortDate(date)}`}</T> : null}
        </T>
        {offers.map((o) => <OfferCard key={o.offer_id} offer={o} action={<OfferAction offer={o} user={user} />} />)}
      </View>
    ) : null;
  return (
    <View>
      {f.origin_airport && f.destination_airport ? (
        <T style={{ marginBottom: 10 }}>
          <T variant="heading">{f.origin_airport.iata_code}</T> {f.origin_airport.city || f.origin_airport.name}  to  <T variant="heading">{f.destination_airport.iata_code}</T> {f.destination_airport.city || f.destination_airport.name}
        </T>
      ) : null}
      {f.note ? <T variant="small" style={{ marginBottom: 12 }}>{f.note}</T> : null}
      {leg("Going", trip.start_date, f.outbound)}
      {leg("Coming back", trip.end_date, f.inbound)}
      {f.links.length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 16, alignItems: "center" }}>
          <T variant="small">Compare more fares:</T>
          {f.links.map((l) => <TextLink key={l.url} label={l.label} url={l.url} />)}
        </View>
      ) : null}
    </View>
  );
}

export function SourcesList({ trip }: { trip: Trip }) {
  const sources = trip.plan?.sources ?? [];
  if (!sources.length) return null;
  return (
    <View style={{ marginTop: 24, gap: 6 }}>
      <T variant="heading">Where this came from</T>
      <T variant="small">The planner read these pages before writing your route.</T>
      {sources.map((s, i) => (
        <Pressable key={s.url} accessibilityRole="link" onPress={() => Linking.openURL(s.url)}>
          <T variant="small" style={{ color: colors.ink }}>
            {i + 1}. {s.title} <T variant="small">({hostname(s.url)})</T>
          </T>
        </Pressable>
      ))}
    </View>
  );
}
