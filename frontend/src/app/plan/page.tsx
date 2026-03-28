"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  MapPin,
  Calendar,
  Users,
  Wallet,
  Sparkles,
  Plane,
  ArrowRight,
  ArrowLeft,
  Loader2,
} from "lucide-react";

const TRAVEL_STYLES = [
  { value: "budget", label: "🎒 Budget", desc: "Hostels, street food, public transport" },
  { value: "comfort", label: "😊 Comfort", desc: "Nice hotels, good restaurants" },
  { value: "luxury", label: "✨ Luxury", desc: "5-star hotels, fine dining, private tours" },
  { value: "adventure", label: "🏔️ Adventure", desc: "Hiking, camping, off-the-beaten-path" },
  { value: "cultural", label: "🎭 Cultural", desc: "Museums, history, local experiences" },
  { value: "relaxation", label: "🏖️ Relaxation", desc: "Beach, spa, slow-paced" },
];

const VIBES = [
  "🎉 Nightlife",
  "🍝 Foodie",
  "📸 Photography",
  "🏛️ History",
  "🌿 Nature",
  "🛍️ Shopping",
  "🎨 Art",
  "⛰️ Outdoor",
  "👨‍👩‍👧 Family",
  "💑 Romantic",
  "🧘 Wellness",
  "🎵 Music",
];

const STEPS = [
  { id: 1, title: "Destination", icon: MapPin },
  { id: 2, title: "When & Who", icon: Calendar },
  { id: 3, title: "Style", icon: Sparkles },
];

export default function PlanPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  // Form state
  const [form, setForm] = useState({
    name: "",
    destination: "",
    starting_location: "",
    travel_dates: { start: "", end: "" },
    duration: 3,
    traveling_with: "Solo",
    adults: 1,
    children: 0,
    budget: 1000,
    budget_currency: "USD",
    travel_style: "comfort",
    vibes: [] as string[],
    interests: "",
    additional_info: "",
  });

  const updateForm = (updates: Partial<typeof form>) => {
    setForm((prev) => ({ ...prev, ...updates }));
  };

  const toggleVibe = (vibe: string) => {
    setForm((prev) => ({
      ...prev,
      vibes: prev.vibes.includes(vibe)
        ? prev.vibes.filter((v) => v !== vibe)
        : [...prev.vibes, vibe],
    }));
  };

  const handleSubmit = async () => {
    if (!form.destination) return;
    setLoading(true);

    try {
      // Step 1: Save trip to PostgreSQL (via Prisma)
      const createRes = await fetch("/api/trips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!createRes.ok) throw new Error("Failed to create trip");
      const { trip_plan_id } = await createRes.json();

      // Step 2: Trigger backend AI generation
      const triggerRes = await fetch("http://localhost:8000/api/plan/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trip_plan_id: trip_plan_id,
          travel_plan: form,
        }),
      });

      if (!triggerRes.ok) {
        console.warn("Backend trigger failed, trip saved to DB without AI generation.");
      }

      router.push(`/plan/${trip_plan_id}`);
    } catch (error) {
      console.error("Error:", error);
      alert("Failed to create trip. Make sure you're logged in.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-gradient-to-br from-emerald-50/50 via-background to-teal-50/50">
      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Progress bar */}
        <div className="flex items-center justify-center gap-2 mb-10">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center gap-2">
              <button
                onClick={() => setStep(s.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  step === s.id
                    ? "bg-emerald-500 text-white shadow-md"
                    : step > s.id
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                <s.icon className="w-4 h-4" />
                {s.title}
              </button>
              {i < STEPS.length - 1 && (
                <div className={`w-8 h-0.5 ${step > s.id ? "bg-emerald-400" : "bg-border"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Destination */}
        {step === 1 && (
          <Card className="border-0 shadow-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-2xl">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-white" />
                </div>
                Where to?
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="destination" className="text-base font-medium">
                  Destination *
                </Label>
                <Input
                  id="destination"
                  placeholder="e.g. Paris, Tokyo, Bali..."
                  value={form.destination}
                  onChange={(e) => updateForm({ destination: e.target.value })}
                  className="h-12 text-lg border-2 focus:border-emerald-500"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="starting" className="text-base font-medium">
                  Starting Location
                </Label>
                <Input
                  id="starting"
                  placeholder="e.g. New York, Mumbai..."
                  value={form.starting_location}
                  onChange={(e) => updateForm({ starting_location: e.target.value })}
                  className="h-12"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="name" className="text-base font-medium">
                  Trip Name (optional)
                </Label>
                <Input
                  id="name"
                  placeholder="e.g. Summer Holiday 2025"
                  value={form.name}
                  onChange={(e) => updateForm({ name: e.target.value })}
                  className="h-12"
                />
              </div>

              <Button
                onClick={() => setStep(2)}
                disabled={!form.destination}
                className="w-full h-12 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white text-base"
              >
                Continue <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step 2: When & Who */}
        {step === 2 && (
          <Card className="border-0 shadow-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-2xl">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-white" />
                </div>
                When & Who
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="font-medium">Start Date</Label>
                  <Input
                    type="date"
                    value={form.travel_dates.start}
                    onChange={(e) =>
                      updateForm({
                        travel_dates: { ...form.travel_dates, start: e.target.value },
                      })
                    }
                    className="h-11"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="font-medium">End Date</Label>
                  <Input
                    type="date"
                    value={form.travel_dates.end}
                    onChange={(e) =>
                      updateForm({
                        travel_dates: { ...form.travel_dates, end: e.target.value },
                      })
                    }
                    className="h-11"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label className="font-medium">Duration (days): {form.duration}</Label>
                <input
                  type="range"
                  min={1}
                  max={30}
                  value={form.duration}
                  onChange={(e) => updateForm({ duration: parseInt(e.target.value) })}
                  className="w-full accent-emerald-500"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>1 day</span>
                  <span>30 days</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="font-medium">Traveling With</Label>
                <Select value={form.traveling_with} onValueChange={(v) => { if (v) updateForm({ traveling_with: v }); }}>
                  <SelectTrigger className="h-11">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Solo">🧍 Solo</SelectItem>
                    <SelectItem value="Couple">💑 Couple</SelectItem>
                    <SelectItem value="Family">👨‍👩‍👧‍👦 Family</SelectItem>
                    <SelectItem value="Friends">👯 Friends</SelectItem>
                    <SelectItem value="Group">👥 Group</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="font-medium">
                    <Users className="w-4 h-4 inline mr-1" /> Adults
                  </Label>
                  <Input
                    type="number"
                    min={1}
                    max={20}
                    value={form.adults}
                    onChange={(e) => updateForm({ adults: parseInt(e.target.value) || 1 })}
                    className="h-11"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="font-medium">Children</Label>
                  <Input
                    type="number"
                    min={0}
                    max={10}
                    value={form.children}
                    onChange={(e) => updateForm({ children: parseInt(e.target.value) || 0 })}
                    className="h-11"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(1)} className="h-11">
                  <ArrowLeft className="w-4 h-4 mr-1" /> Back
                </Button>
                <Button
                  onClick={() => setStep(3)}
                  className="flex-1 h-11 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white"
                >
                  Continue <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Style & Budget */}
        {step === 3 && (
          <Card className="border-0 shadow-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-2xl">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                Style & Budget
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <Label className="text-base font-medium">Travel Style</Label>
                <div className="grid grid-cols-2 gap-3">
                  {TRAVEL_STYLES.map((s) => (
                    <button
                      key={s.value}
                      onClick={() => updateForm({ travel_style: s.value })}
                      className={`text-left p-3 rounded-xl border-2 transition-all ${
                        form.travel_style === s.value
                          ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/20"
                          : "border-border hover:border-emerald-300"
                      }`}
                    >
                      <div className="font-medium text-sm">{s.label}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">{s.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <Label className="text-base font-medium">
                  <Wallet className="w-4 h-4 inline mr-1" />
                  Budget per person: ${form.budget}
                </Label>
                <input
                  type="range"
                  min={100}
                  max={10000}
                  step={100}
                  value={form.budget}
                  onChange={(e) => updateForm({ budget: parseInt(e.target.value) })}
                  className="w-full accent-emerald-500"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>$100</span>
                  <span>$10,000+</span>
                </div>
              </div>

              <div className="space-y-3">
                <Label className="text-base font-medium">Trip Vibes (select any)</Label>
                <div className="flex flex-wrap gap-2">
                  {VIBES.map((vibe) => (
                    <button
                      key={vibe}
                      onClick={() => toggleVibe(vibe)}
                      className={`px-3 py-1.5 rounded-full text-sm transition-all ${
                        form.vibes.includes(vibe)
                          ? "bg-emerald-500 text-white shadow-sm"
                          : "bg-muted hover:bg-muted/80"
                      }`}
                    >
                      {vibe}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label className="font-medium">Any specific interests or requests?</Label>
                <Textarea
                  placeholder="e.g. I love street food, want to see cherry blossoms, looking for hidden gem cafes..."
                  value={form.interests}
                  onChange={(e) => updateForm({ interests: e.target.value })}
                  rows={3}
                />
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(2)} className="h-12">
                  <ArrowLeft className="w-4 h-4 mr-1" /> Back
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={loading || !form.destination}
                  className="flex-1 h-12 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white text-base shadow-lg"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Creating Your Trip...
                    </>
                  ) : (
                    <>
                      <Plane className="w-5 h-5 mr-2" />
                      Generate My Itinerary
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
