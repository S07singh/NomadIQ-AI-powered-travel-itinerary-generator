"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Field, Loading, Notice, Page, PageTitle, SelectField } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useAuth, useRequireUser } from "@/lib/auth";
import type { TravelStyle, Traveler, User } from "@/lib/types";

const EMPTY = { label: "", title: "mr", given_name: "", family_name: "", born_on: "", phone: "", email: "" };

export default function ProfilePage() {
  const user = useRequireUser();
  const { setUser, logout } = useAuth();
  const router = useRouter();
  const [travelers, setTravelers] = useState<Traveler[]>([]);
  const [draft, setDraft] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) api.travelers().then(setTravelers).catch(() => undefined);
  }, [user]);

  if (!user) return <Page><Loading /></Page>;

  const addTraveler = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const t = await api.addTraveler({
        label: draft.label || draft.given_name,
        title: draft.title as "mr",
        given_name: draft.given_name,
        family_name: draft.family_name,
        born_on: draft.born_on || null,
        gender: ["ms", "mrs", "miss"].includes(draft.title) ? "f" : "m",
        phone: draft.phone || null,
        email: draft.email || null,
      });
      setTravelers((cur) => [...cur, t]);
      setDraft(EMPTY);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save traveler.");
    }
  };

  const removeTraveler = async (id: string) => {
    await api.deleteTraveler(id);
    setTravelers((cur) => cur.filter((t) => t.id !== id));
  };

  return (
    <Page>
      <PageTitle sub={user.email}>Profile</PageTitle>
      {error ? <div className="mb-6"><Notice>{error}</Notice></div> : null}
      <div className="grid lg:grid-cols-2 gap-16">
        <PreferencesForm user={user} onSaved={setUser} onError={setError} />

        <section>
          <h2 className="heading text-2xl">Travelers</h2>
          <p className="text-slate mt-2 max-w-[50ch]">Saved details make booking one tap, and let the assistant hold fares for you by voice.</p>
          {travelers.length ? (
            <ul className="mt-5 divide-y divide-rule border-y border-rule">
              {travelers.map((t) => (
                <li key={t.id} className="py-3 flex items-center justify-between gap-4">
                  <span>
                    <span className="font-bold">{t.given_name} {t.family_name}</span>
                    <span className="text-slate">{t.label && t.label !== t.given_name ? `, ${t.label}` : ""}</span>
                  </span>
                  <button onClick={() => removeTraveler(t.id)} className="text-sm font-bold text-brick hover:underline underline-offset-4">Remove</button>
                </li>
              ))}
            </ul>
          ) : null}
          <form onSubmit={addTraveler} className="mt-6 grid grid-cols-2 gap-4">
            <SelectField label="Title" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}>
              {["mr", "ms", "mrs", "miss", "dr"].map((t) => <option key={t} value={t}>{t[0].toUpperCase() + t.slice(1)}</option>)}
            </SelectField>
            <Field label="Label" placeholder="Me, Mum, Arjun" value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} />
            <Field label="First name" required value={draft.given_name} onChange={(e) => setDraft({ ...draft, given_name: e.target.value })} />
            <Field label="Last name" required value={draft.family_name} onChange={(e) => setDraft({ ...draft, family_name: e.target.value })} />
            <Field label="Date of birth" type="date" value={draft.born_on} onChange={(e) => setDraft({ ...draft, born_on: e.target.value })} />
            <Field label="Mobile" type="tel" value={draft.phone} onChange={(e) => setDraft({ ...draft, phone: e.target.value })} />
            <Button type="submit" variant="quiet" className="col-span-2 sm:col-span-1">Save traveler</Button>
          </form>
        </section>
      </div>

      <div className="mt-16 pt-8 border-t border-rule">
        <Button
          variant="quiet"
          onClick={async () => {
            await logout();
            router.replace("/");
          }}
        >
          Sign out
        </Button>
      </div>
    </Page>
  );
}

function PreferencesForm({ user, onSaved, onError }: { user: User; onSaved: (u: User) => void; onError: (msg: string | null) => void }) {
  const [prefs, setPrefs] = useState({
    name: user.name,
    home_city: user.preferences.home_city ?? "",
    home_airport: user.preferences.home_airport ?? "",
    currency: user.preferences.currency,
    travel_style: user.preferences.travel_style,
  });
  const [saved, setSaved] = useState(false);

  const savePrefs = async (e: React.FormEvent) => {
    e.preventDefault();
    onError(null);
    try {
      const updated = await api.updateMe({
        name: prefs.name,
        preferences: { home_city: prefs.home_city || null, home_airport: prefs.home_airport ? prefs.home_airport.toUpperCase() : null, currency: prefs.currency, travel_style: prefs.travel_style },
      });
      onSaved(updated);
      setSaved(true);
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Couldn't save. Try again.");
    }
  };

  return (
    <form onSubmit={savePrefs} className="space-y-5 max-w-[480px]">
      <h2 className="heading text-2xl">Your defaults</h2>
      <p className="text-slate -mt-3">Used to fill in searches and to plan trips that fit how you travel.</p>
      <Field label="Name" value={prefs.name} onChange={(e) => setPrefs({ ...prefs, name: e.target.value })} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Home city" placeholder="Bengaluru" value={prefs.home_city} onChange={(e) => setPrefs({ ...prefs, home_city: e.target.value })} />
        <Field label="Nearest airport" placeholder="BLR" maxLength={3} value={prefs.home_airport} onChange={(e) => setPrefs({ ...prefs, home_airport: e.target.value })} />
        <SelectField label="Currency" value={prefs.currency} onChange={(e) => setPrefs({ ...prefs, currency: e.target.value })}>
          {["INR", "USD", "EUR", "GBP", "AED", "SGD"].map((c) => <option key={c}>{c}</option>)}
        </SelectField>
        <SelectField label="Travel style" value={prefs.travel_style} onChange={(e) => setPrefs({ ...prefs, travel_style: e.target.value as TravelStyle })}>
          {["backpacker", "budget", "comfort", "luxury"].map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
        </SelectField>
      </div>
      {saved ? <Notice tone="success">Preferences saved.</Notice> : null}
      <Button type="submit">Save preferences</Button>
    </form>
  );
}
