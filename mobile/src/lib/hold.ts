import { router } from "expo-router";
import { Alert } from "react-native";
import { ApiError, api } from "@/api/client";
import type { AnyOffer, User } from "@/api/types";
import { newIdempotencyKey } from "./format";

/**
 * Hold a fare for the signed-in user using their saved travelers, then open the review screen.
 * Nothing is charged here: payment happens only on the booking screen's explicit confirm.
 */
export async function holdFare(offer: AnyOffer, user: User): Promise<void> {
  const needed = offer.kind === "flight" ? offer.passengers : 1;
  const travelers = await api.travelers();
  if (travelers.length < needed) {
    Alert.alert(
      "Add traveler details",
      needed > 1 ? `This fare is for ${needed} people. Save ${needed} travelers in your profile first.` : "Save your name and phone in your profile once, then booking is one tap.",
      [{ text: "Not now", style: "cancel" }, { text: "Open profile", onPress: () => router.push("/profile") }],
    );
    return;
  }
  const lead = travelers[0];
  if (!lead.phone) {
    Alert.alert("Add a phone number", "Tickets and schedule changes are sent to the lead traveler's phone.", [
      { text: "Not now", style: "cancel" },
      { text: "Open profile", onPress: () => router.push("/profile") },
    ]);
    return;
  }
  try {
    const booking = await api.createBooking(
      { offer_id: offer.offer_id, traveler_ids: travelers.slice(0, needed).map((t) => t.id), contact: { email: lead.email || user.email, phone: lead.phone } },
      newIdempotencyKey(),
    );
    router.push(`/booking/${booking.id}`);
  } catch (err) {
    const e = err as ApiError;
    Alert.alert("Couldn't hold this fare", e.code === "offer_expired" ? "The price expired. Search again for current fares." : e.message);
  }
}
