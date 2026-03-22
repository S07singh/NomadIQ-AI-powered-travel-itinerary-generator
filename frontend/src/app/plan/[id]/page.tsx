"use client";

import { useState, useEffect, useRef, use } from "react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import {
  Plane,
  Hotel,
  UtensilsCrossed,
  MapPin,
  Wallet,
  Lightbulb,
  Calendar,
  MessageSquare,
  Send,
  Loader2,
  CheckCircle,
  Clock,
  X,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

interface PlanData {
  status: string;
  current_step: string | null;
  itinerary: string | null;
  error: string | null;
  created_at: string | null;
}

interface DayPlan {
  day: number;
  date: string;
  morning: string;
  afternoon: string;
  evening: string;
  notes: string;
}

interface ParsedItinerary {
  day_by_day_plan: DayPlan[];
  hotels: { hotel_name: string; price: string; rating: string; address: string; amenities: string[]; description: string }[];
  flights: { airline: string; price: string; departure_time: string; arrival_time: string; duration: string; stops: number }[];
  attractions: { name: string; description: string; location: string; estimated_cost: string; visit_duration: string }[];
  restaurants: { name: string; cuisine: string; price_range: string; description: string; location: string }[];
  budget_summary: string;
  tips: string[];
  total_estimated_cost: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export default function PlanDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [parsedItinerary, setParsedItinerary] = useState<ParsedItinerary | null>(null);
  const [rawResponses, setRawResponses] = useState<Record<string, string>>({});
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Poll for status updates
  useEffect(() => {
    let interval: NodeJS.Timeout;

    const fetchPlan = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/plan/${id}`);
        if (!res.ok) return;
        const data: PlanData = await res.json();
        setPlan(data);

        if (data.itinerary) {
          try {
            const parsed = JSON.parse(data.itinerary);
            if (parsed.itinerary) {
              const innerParsed = typeof parsed.itinerary === "string" 
                ? JSON.parse(parsed.itinerary) 
                : parsed.itinerary;
              setParsedItinerary(innerParsed);
            }
            if (parsed.raw_responses) {
              setRawResponses(parsed.raw_responses);
            }
          } catch {
            console.error("Failed to parse itinerary JSON");
          }
        }

        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch (error) {
        console.error("Error fetching plan:", error);
      }
    };

    fetchPlan();
    interval = setInterval(fetchPlan, 3000);
    return () => clearInterval(interval);
  }, [id]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const sendChatMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const msg = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: msg }]);
    setChatLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trip_plan_id: id, message: msg }),
      });

      if (!res.ok) throw new Error("Chat request failed");
      const data = await res.json();
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.message || "Itinerary updated!" },
      ]);

      // Re-fetch the updated plan
      const planRes = await fetch(`http://localhost:8000/api/plan/${id}`);
      if (planRes.ok) {
        const planData = await planRes.json();
        setPlan(planData);
        if (planData.itinerary) {
          try {
            const parsed = JSON.parse(planData.itinerary);
            if (parsed.itinerary) {
              const inner = typeof parsed.itinerary === "string"
                ? JSON.parse(parsed.itinerary)
                : parsed.itinerary;
              setParsedItinerary(inner);
            }
          } catch { /* ignore */ }
        }
      }
    } catch {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Loading / Processing State
  if (!plan || plan.status === "pending" || plan.status === "processing") {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-gradient-to-br from-emerald-50/50 via-background to-teal-50/50">
        <div className="text-center max-w-md">
          <div className="relative w-20 h-20 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 animate-pulse" />
            <div className="absolute inset-2 rounded-full bg-background flex items-center justify-center">
              <Plane className="w-8 h-8 text-emerald-500 animate-bounce" />
            </div>
          </div>
          <h2 className="text-2xl font-bold mb-2">Creating Your Trip</h2>
          <p className="text-muted-foreground mb-6">
            {plan?.current_step || "Preparing AI agents..."}
          </p>
          <div className="space-y-2">
            {[
              "Researching destination attractions",
              "Searching for hotels",
              "Finding restaurants",
              "Creating day-by-day itinerary",
              "Analyzing budget",
              "Finalizing your travel plan",
            ].map((step) => {
              const isCurrent = plan?.current_step === step;
              const isDone = plan?.current_step
                ? [
                    "Researching destination attractions",
                    "Searching for hotels",
                    "Finding restaurants",
                    "Creating day-by-day itinerary",
                    "Analyzing budget",
                    "Finalizing your travel plan",
                  ].indexOf(step) <
                  [
                    "Researching destination attractions",
                    "Searching for hotels",
                    "Finding restaurants",
                    "Creating day-by-day itinerary",
                    "Analyzing budget",
                    "Finalizing your travel plan",
                  ].indexOf(plan.current_step)
                : false;
              return (
                <div
                  key={step}
                  className={`flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all ${
                    isCurrent
                      ? "bg-emerald-100 text-emerald-800 font-medium"
                      : isDone
                      ? "text-emerald-600"
                      : "text-muted-foreground"
                  }`}
                >
                  {isDone ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Clock className="w-4 h-4" />
                  )}
                  {step}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (plan.status === "failed") {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-destructive mb-2">Generation Failed</h2>
          <p className="text-muted-foreground mb-4">{plan.error || "Unknown error"}</p>
          <Link href="/plan">
            <Button>Try Again</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Completed — show itinerary
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-gradient-to-br from-emerald-50/30 via-background to-teal-50/30">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Link href="/plans">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-1" /> Back
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold">Your Travel Plan</h1>
              <p className="text-muted-foreground text-sm">
                {parsedItinerary?.total_estimated_cost && (
                  <span className="text-emerald-600 font-medium">
                    Est. cost: {parsedItinerary.total_estimated_cost} •{" "}
                  </span>
                )}
                {parsedItinerary?.day_by_day_plan?.length || 0} days planned
              </p>
            </div>
          </div>
          <Button
            onClick={() => setChatOpen(!chatOpen)}
            className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            {chatOpen ? "Close Chat" : "Modify with AI"}
          </Button>
        </div>

        <div className="flex gap-6">
          {/* Main content */}
          <div className={`flex-1 ${chatOpen ? "max-w-[calc(100%-380px)]" : ""}`}>
            <Tabs defaultValue="itinerary" className="w-full">
              <TabsList className="grid w-full grid-cols-5 mb-6">
                <TabsTrigger value="itinerary">
                  <Calendar className="w-4 h-4 mr-1.5" /> Itinerary
                </TabsTrigger>
                <TabsTrigger value="hotels">
                  <Hotel className="w-4 h-4 mr-1.5" /> Hotels
                </TabsTrigger>
                <TabsTrigger value="restaurants">
                  <UtensilsCrossed className="w-4 h-4 mr-1.5" /> Food
                </TabsTrigger>
                <TabsTrigger value="attractions">
                  <MapPin className="w-4 h-4 mr-1.5" /> Places
                </TabsTrigger>
                <TabsTrigger value="budget">
                  <Wallet className="w-4 h-4 mr-1.5" /> Budget
                </TabsTrigger>
              </TabsList>

              {/* Itinerary Tab */}
              <TabsContent value="itinerary" className="space-y-4">
                {parsedItinerary?.day_by_day_plan?.map((day) => (
                  <Card key={day.day} className="overflow-hidden hover:shadow-lg transition-shadow">
                    <CardHeader className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white py-3 px-5">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Calendar className="w-5 h-5" />
                        Day {day.day} {day.date && `— ${day.date}`}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-5 space-y-4">
                      {day.morning && (
                        <div>
                          <h4 className="font-semibold text-sm text-amber-600 mb-1">🌅 Morning</h4>
                          <div className="text-sm text-muted-foreground prose prose-sm max-w-none">
                            <ReactMarkdown>{day.morning}</ReactMarkdown>
                          </div>
                        </div>
                      )}
                      {day.afternoon && (
                        <div>
                          <Separator className="my-2" />
                          <h4 className="font-semibold text-sm text-orange-600 mb-1">☀️ Afternoon</h4>
                          <div className="text-sm text-muted-foreground prose prose-sm max-w-none">
                            <ReactMarkdown>{day.afternoon}</ReactMarkdown>
                          </div>
                        </div>
                      )}
                      {day.evening && (
                        <div>
                          <Separator className="my-2" />
                          <h4 className="font-semibold text-sm text-indigo-600 mb-1">🌙 Evening</h4>
                          <div className="text-sm text-muted-foreground prose prose-sm max-w-none">
                            <ReactMarkdown>{day.evening}</ReactMarkdown>
                          </div>
                        </div>
                      )}
                      {day.notes && (
                        <div className="bg-amber-50 dark:bg-amber-950/20 rounded-lg p-3 mt-3">
                          <p className="text-sm text-amber-700 dark:text-amber-300">
                            <Lightbulb className="w-4 h-4 inline mr-1" /> {day.notes}
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
                {/* Also render raw response if no structured data */}
                {(!parsedItinerary?.day_by_day_plan || parsedItinerary.day_by_day_plan.length === 0) && rawResponses.itinerary && (
                  <Card>
                    <CardContent className="p-6 prose prose-sm max-w-none">
                      <ReactMarkdown>{rawResponses.itinerary}</ReactMarkdown>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Hotels Tab */}
              <TabsContent value="hotels" className="space-y-4">
                {parsedItinerary?.hotels?.map((hotel, i) => (
                  <Card key={i} className="hover:shadow-lg transition-shadow">
                    <CardContent className="p-5">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-lg font-semibold">{hotel.hotel_name}</h3>
                          <p className="text-sm text-muted-foreground mt-1">{hotel.address}</p>
                        </div>
                        <div className="text-right">
                          <span className="text-xl font-bold text-emerald-600">{hotel.price}</span>
                          {hotel.rating && <p className="text-sm text-amber-500">⭐ {hotel.rating}</p>}
                        </div>
                      </div>
                      {hotel.description && <p className="text-sm mt-3">{hotel.description}</p>}
                      {hotel.amenities?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {hotel.amenities.map((a, j) => (
                            <Badge key={j} variant="secondary" className="text-xs">{a}</Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
                {(!parsedItinerary?.hotels || parsedItinerary.hotels.length === 0) && rawResponses.hotel && (
                  <Card><CardContent className="p-6 prose prose-sm max-w-none"><ReactMarkdown>{rawResponses.hotel}</ReactMarkdown></CardContent></Card>
                )}
              </TabsContent>

              {/* Restaurants Tab */}
              <TabsContent value="restaurants" className="space-y-4">
                {parsedItinerary?.restaurants?.map((rest, i) => (
                  <Card key={i} className="hover:shadow-lg transition-shadow">
                    <CardContent className="p-5">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-semibold text-lg">{rest.name}</h3>
                          <p className="text-sm text-muted-foreground">{rest.cuisine} • {rest.location}</p>
                        </div>
                        <Badge variant="outline" className="text-emerald-600">{rest.price_range}</Badge>
                      </div>
                      {rest.description && <p className="text-sm mt-2 text-muted-foreground">{rest.description}</p>}
                    </CardContent>
                  </Card>
                ))}
                {(!parsedItinerary?.restaurants || parsedItinerary.restaurants.length === 0) && rawResponses.dining && (
                  <Card><CardContent className="p-6 prose prose-sm max-w-none"><ReactMarkdown>{rawResponses.dining}</ReactMarkdown></CardContent></Card>
                )}
              </TabsContent>

              {/* Attractions Tab */}
              <TabsContent value="attractions" className="space-y-4">
                {parsedItinerary?.attractions?.map((attr, i) => (
                  <Card key={i} className="hover:shadow-lg transition-shadow">
                    <CardContent className="p-5">
                      <h3 className="font-semibold text-lg">{attr.name}</h3>
                      <p className="text-sm text-muted-foreground mt-1">{attr.description}</p>
                      <div className="flex gap-4 mt-3 text-sm">
                        <span><MapPin className="w-3 h-3 inline mr-1" />{attr.location}</span>
                        <span><Clock className="w-3 h-3 inline mr-1" />{attr.visit_duration}</span>
                        <span className="text-emerald-600 font-medium">{attr.estimated_cost}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {(!parsedItinerary?.attractions || parsedItinerary.attractions.length === 0) && rawResponses.destination && (
                  <Card><CardContent className="p-6 prose prose-sm max-w-none"><ReactMarkdown>{rawResponses.destination}</ReactMarkdown></CardContent></Card>
                )}
              </TabsContent>

              {/* Budget Tab */}
              <TabsContent value="budget">
                <Card>
                  <CardContent className="p-6">
                    {parsedItinerary?.total_estimated_cost && (
                      <div className="text-center mb-6">
                        <p className="text-sm text-muted-foreground">Total Estimated Cost</p>
                        <p className="text-4xl font-bold text-emerald-600">{parsedItinerary.total_estimated_cost}</p>
                      </div>
                    )}
                    {parsedItinerary?.budget_summary && (
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown>{parsedItinerary.budget_summary}</ReactMarkdown>
                      </div>
                    )}
                    {rawResponses.budget && (
                      <div className="prose prose-sm max-w-none mt-4">
                        <ReactMarkdown>{rawResponses.budget}</ReactMarkdown>
                      </div>
                    )}
                    {parsedItinerary?.tips && parsedItinerary.tips.length > 0 && (
                      <div className="mt-6">
                        <h3 className="font-semibold mb-3 flex items-center gap-2">
                          <Lightbulb className="w-5 h-5 text-amber-500" /> Travel Tips
                        </h3>
                        <ul className="space-y-2">
                          {parsedItinerary.tips.map((tip, i) => (
                            <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                              <span className="text-emerald-500 mt-0.5">•</span> {tip}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>

          {/* Chat Panel */}
          {chatOpen && (
            <div className="w-[360px] shrink-0">
              <Card className="sticky top-20 h-[calc(100vh-8rem)] flex flex-col">
                <CardHeader className="py-3 px-4 border-b flex-row items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                      <MessageSquare className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <CardTitle className="text-sm">AI Trip Editor</CardTitle>
                      <p className="text-xs text-muted-foreground">Modify your plan</p>
                    </div>
                  </div>
                  <button onClick={() => setChatOpen(false)}>
                    <X className="w-4 h-4 text-muted-foreground" />
                  </button>
                </CardHeader>
                <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
                  {chatMessages.length === 0 && (
                    <div className="text-center text-sm text-muted-foreground py-8">
                      <MessageSquare className="w-10 h-10 mx-auto mb-3 text-emerald-300" />
                      <p className="font-medium mb-1">Ask me anything!</p>
                      <p>Try:</p>
                      <div className="space-y-1.5 mt-3">
                        {[
                          "Add nightlife to day 2",
                          "Make this trip cheaper",
                          "Replace the museum with outdoor activities",
                        ].map((suggestion) => (
                          <button
                            key={suggestion}
                            onClick={() => {
                              setChatInput(suggestion);
                            }}
                            className="block w-full text-left text-xs bg-muted rounded-lg px-3 py-2 hover:bg-muted/80 transition-colors"
                          >
                            &ldquo;{suggestion}&rdquo;
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {chatMessages.map((msg, i) => (
                    <div
                      key={i}
                      className={`text-sm p-3 rounded-xl max-w-[90%] ${
                        msg.role === "user"
                          ? "bg-emerald-500 text-white ml-auto"
                          : "bg-muted"
                      }`}
                    >
                      {msg.content}
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" /> Modifying itinerary...
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </CardContent>
                <div className="border-t p-3">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      sendChatMessage();
                    }}
                    className="flex gap-2"
                  >
                    <Input
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Type a modification..."
                      className="flex-1"
                      disabled={chatLoading}
                    />
                    <Button
                      type="submit"
                      size="sm"
                      disabled={chatLoading || !chatInput.trim()}
                      className="bg-emerald-500 hover:bg-emerald-600 text-white"
                    >
                      <Send className="w-4 h-4" />
                    </Button>
                  </form>
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
