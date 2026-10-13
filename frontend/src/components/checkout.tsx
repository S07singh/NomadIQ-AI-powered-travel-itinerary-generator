"use client";

import clsx from "clsx";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money, newIdempotencyKey } from "@/lib/format";
import type { AnyOffer, Traveler } from "@/lib/types";
import { Button, Field, Notice, SelectField } from "./ui";

/** Choose travelers + contact for an offer, then create a held booking awaiting confirmation. */
export function Checkout({ offer, tripId, onClose }: { offer: AnyOffer; tripId?: string; onClose: () => void }) {
  const { user } = useAuth();
  const router = useRouter();
  const needed = offer.kind === "flight" ? offer.passengers : 1;
  const [saved, setSaved] = useState<Traveler[] | null>(null);
  const [chosen, setChosen] = useState<string[]>([]);
  const [draft, setDraft] = useState({ title: "mr", given_name: "", family_name: "", born_on: "", gender: "m", phone: "" });
  const [email, setEmail] = useState(user?.email ?? "");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const idempotencyKey = useMemo(() => newIdempotencyKey(), []);

  useEffect(() => {
    api
      .travelers()
      .then((list) => {
        setSaved(list);
        setChosen(list.slice(0, needed).map((t) => t.id));
        if (list[0]?.phone) setPhone(list[0].phone);
      })
      .catch(() => setSaved([]));
  }, [needed]);

  const toggle = (id: string) =>
    setChosen((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : cur.length >= needed ? [...cur.slice(1), id] : [...cur, id]));

  const hold = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      let ids = chosen;
      if (saved && saved.length === 0) {
        const t = await api.addTraveler({
          label: "Me",
          title: draft.title as "mr",
          given_name: draft.given_name,
          family_name: draft.family_name,
          born_on: draft.born_on || null,
          gender: draft.gender as "m",
          phone: phone || null,
          email: email || null,
        });
        ids = [t.id];
      }
      if (ids.length !== needed) throw new ApiError(422, "traveler_mismatch", `Choose ${needed} traveler${needed > 1 ? "s" : ""} for this fare.`);
      const booking = await api.createBooking({ offer_id: offer.offer_id, traveler_ids: ids, contact: { email, phone }, trip_id: tripId }, idempotencyKey);
      router.push(`/bookings/${booking.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? (err.code === "offer_expired" ? "This fare has expired. Search again for current prices." : err.message) : "Couldn't hold this fare. Try again.");
      setBusy(false);
    }
  };

  return (
    <form onSubmit={hold} className="mt-5 border-t-2 border-ink pt-5 grid lg:grid-cols-[1fr_260px] gap-8">
      <div className="space-y-5">
        <h3 className="heading text-lg">Who&apos;s traveling</h3>
        {saved === null ? <p className="text-slate">Loading saved travelers</p> : null}
        {saved && saved.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {saved.map((t) => (
              <button
                type="button"
                key={t.id}
                aria-pressed={chosen.includes(t.id)}
                onClick={() => toggle(t.id)}
                className={clsx("h-10 px-4 rounded-full border-2 font-semibold", chosen.includes(t.id) ? "border-ink bg-ink text-white" : "border-rule bg-sheet hover:border-ink/50")}
              >
                {t.given_name} {t.family_name}
              </button>
            ))}
          </div>
        ) : null}
        {saved && saved.length === 0 ? (
          <div className="grid sm:grid-cols-[110px_1fr_1fr] gap-4">
            <SelectField label="Title" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value, gender: ["ms", "mrs", "miss"].includes(e.target.value) ? "f" : "m" })}>
              {["mr", "ms", "mrs", "miss", "dr"].map((t) => <option key={t} value={t}>{t[0].toUpperCase() + t.slice(1)}</option>)}
            </SelectField>
            <Field label="First name" required value={draft.given_name} onChange={(e) => setDraft({ ...draft, given_name: e.target.value })} />
            <Field label="Last name" required value={draft.family_name} onChange={(e) => setDraft({ ...draft, family_name: e.target.value })} />
            <Field label="Date of birth" type="date" required={offer.kind === "flight"} value={draft.born_on} onChange={(e) => setDraft({ ...draft, born_on: e.target.value })} className="sm:col-span-2" />
          </div>
        ) : null}
        {saved && saved.length === 0 ? <p className="text-sm text-slate">We&apos;ll save these details so next time it&apos;s one tap.</p> : null}
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Email for tickets" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <Field label="Mobile number" type="tel" required minLength={6} placeholder="+91 98765 43210" value={phone} onChange={(e) => setPhone(e.target.value)} />
        </div>
        {error ? <Notice>{error}</Notice> : null}
      </div>
      <div className="lg:border-l lg:border-rule lg:pl-8">
        <p className="text-slate">Total</p>
        <p className="display text-4xl tabular">{money(offer.price)}</p>
        <p className="mt-2 text-sm text-slate">We check the price with the airline or hotel before you pay. Nothing is charged yet.</p>
        <div className="mt-5 flex flex-col gap-2">
          <Button type="submit" disabled={busy}>{busy ? "Holding fare" : "Hold this fare"}</Button>
          <Button type="button" variant="quiet" onClick={onClose}>Back to results</Button>
        </div>
      </div>
    </form>
  );
}
