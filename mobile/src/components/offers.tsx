import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";
import type { AnyOffer, FlightOffer, HotelOffer, TransportOffer } from "@/api/types";
import { clock, duration, money, shortDate } from "@/lib/format";
import { colors } from "@/theme";
import { Photo, T } from "./ui";

function Times({ dep, arr, from, to, mins, stops }: { dep: string; arr: string; from: string; to: string; mins: number; stops?: number }) {
  return (
    <View style={styles.times}>
      <View>
        <T variant="title" style={{ fontSize: 22 }}>{clock(dep)}</T>
        <T variant="small" style={{ fontFamily: "Overpass_700Bold" }}>{from}</T>
      </View>
      <View style={{ flex: 1, alignItems: "center", paddingHorizontal: 8 }}>
        <T variant="small">{duration(mins)}</T>
        <View style={styles.bar} />
        {stops !== undefined ? <T variant="small">{stops === 0 ? "Direct" : `${stops} stop${stops > 1 ? "s" : ""}`}</T> : null}
      </View>
      <View style={{ alignItems: "flex-end" }}>
        <T variant="title" style={{ fontSize: 22 }}>
          {clock(arr)}
          {arr.slice(0, 10) > dep.slice(0, 10) ? <T variant="small" style={{ color: colors.brick }}> +1</T> : null}
        </T>
        <T variant="small" style={{ fontFamily: "Overpass_700Bold" }}>{to}</T>
      </View>
    </View>
  );
}

function headline(offer: AnyOffer): { title: string; sub: string } {
  switch (offer.kind) {
    case "flight": {
      const f = offer as FlightOffer;
      const carriers = Array.from(new Set(f.slices.flatMap((s) => s.segments.map((g) => g.carrier))));
      return { title: carriers.join(", "), sub: `${f.slices[0].segments.map((g) => g.flight_number).join(", ")}, ${shortDate(f.slices[0].departure_at)}` };
    }
    case "train":
    case "bus": {
      const t = offer as TransportOffer;
      const seats = t.seats_available == null ? "" : t.seats_available === 0 ? ", waitlist" : `, ${t.seats_available} seats left`;
      return { title: t.service_name, sub: `${t.kind === "train" ? `No. ${t.service_number}` : t.operator}, ${t.travel_class}${seats}` };
    }
    case "hotel": {
      const h = offer as HotelOffer;
      return { title: h.name, sub: `${h.star_rating ? `${h.star_rating} star, ` : ""}${h.room_name}, ${h.nights} night${h.nights > 1 ? "s" : ""}` };
    }
    default:
      return { title: offer.title, sub: offer.refundable ? "Refundable" : "" };
  }
}

/** One offer as a card row. `action` renders under the price (Select / Book this). */
export function OfferCard({ offer, action }: { offer: AnyOffer; action?: ReactNode }) {
  const { title, sub } = headline(offer);
  const photo = offer.kind === "hotel" || offer.kind === "activity" ? offer.images[0] : null;
  return (
    <View style={styles.card}>
      {photo ? <Photo image={photo} thumb style={{ height: 140, marginBottom: 12 }} /> : null}
      <T variant="heading">{title}</T>
      <T variant="small">{sub}</T>
      {offer.kind === "flight"
        ? (offer as FlightOffer).slices.map((s, i) => (
            <Times key={i} dep={s.departure_at} arr={s.arrival_at} from={s.origin} to={s.destination} mins={s.duration_minutes} stops={s.stops} />
          ))
        : null}
      {offer.kind === "train" || offer.kind === "bus" ? (
        <Times dep={(offer as TransportOffer).departure_at} arr={(offer as TransportOffer).arrival_at} from={(offer as TransportOffer).origin} to={(offer as TransportOffer).destination} mins={(offer as TransportOffer).duration_minutes} />
      ) : null}
      <View style={styles.footer}>
        <View>
          <T variant="title" style={{ fontSize: 24 }}>{money(offer.price)}</T>
          <T variant="small">{offer.refundable ? "Refundable" : "Non-refundable"}</T>
        </View>
        {action}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { paddingVertical: 18, borderBottomWidth: 1, borderBottomColor: colors.rule },
  times: { flexDirection: "row", alignItems: "center", marginTop: 12 },
  bar: { alignSelf: "stretch", height: 3, borderRadius: 2, backgroundColor: colors.ink, marginVertical: 4 },
  footer: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 14, gap: 12 },
});
