"use client";

import { useState, useEffect, useRef, use } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ReactMarkdown from "react-markdown";
import {
  MapPin,
  Hotel,
  UtensilsCrossed,
  Calendar,
  Wallet,
  Loader2,
  CheckCircle,
  Send,
  X,
  MessageSquare,
  Clock,
  AlertCircle,
  Sparkles,
} from "lucide-react";

interface PlanData {
  trip_plan_id: string;
  status: string;
  current_step: string | null;
  itinerary: Record<string, unknown> | null;
  raw_responses: Record<string, unknown> | null;
  error: string | null;
  name: string;
  destination: string;
  duration: number;
  created_at: string;
  chat_messages: Array<{ role: string; content: string; created_at: string }>;
}

const STEPS = [
  "Researching destination",
  "Finding hotels",
  "Discovering restaurants",
  "Creating itinerary",
  "Calculating budget",
  "Finalizing plan",
];

export default function PlanDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessage, setChatMessage] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [chatMessages, setChatMessages] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch plan data from Prisma API
  const fetchPlan = async () => {
    try {
      const res = await fetch(`/api/trips/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      setPlan(data);
      setChatMessages(data.chat_messages || []);

      // If still processing, also poll the backend for AI status
      if (data.status === "pending" || data.status === "processing") {
        pollBackendStatus();
      }
    } catch (err) {
      console.error("Error fetching plan:", err);
    } finally {
      setLoading(false);
    }
  };

  // Poll the backend for AI generation status and sync to Prisma
  const pollBackendStatus = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/plan/${id}`);
      if (!res.ok) return;
      const backendData = await res.json();

      // Sync backend status to Prisma
      if (
        backendData.status === "completed" ||
        backendData.status === "failed"
      ) {
        let itineraryData = null;
        let rawData = null;

        if (backendData.itinerary) {
          try {
            const parsed =
              typeof backendData.itinerary === "string"
                ? JSON.parse(backendData.itinerary)
                : backendData.itinerary;
            itineraryData = parsed.itinerary || parsed;
            rawData = parsed.raw_responses || null;
          } catch {
            itineraryData = backendData.itinerary;
          }
        }

        await fetch(`/api/trips/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            status: backendData.status,
            current_step: backendData.current_step,
            itinerary: itineraryData,
            raw_responses: rawData,
            error: backendData.error,
          }),
        });
      } else {
        // Update just status/step
        await fetch(`/api/trips/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            status: backendData.status,
            current_step: backendData.current_step,
          }),
        });
      }

      // Re-fetch from Prisma to update UI
      const updatedRes = await fetch(`/api/trips/${id}`);
      if (updatedRes.ok) {
        const updatedData = await updatedRes.json();
        setPlan(updatedData);
      }
    } catch (err) {
      console.error("Backend poll error:", err);
    }
  };

  useEffect(() => {
    fetchPlan();

    // Poll every 3 seconds while processing
    pollRef.current = setInterval(() => {
      fetchPlan();
    }, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Stop polling when completed/failed
  useEffect(() => {
    if (
      plan &&
      (plan.status === "completed" || plan.status === "failed") &&
      pollRef.current
    ) {
      clearInterval(pollRef.current);
    }
  }, [plan?.status]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleChatSend = async () => {
    if (!chatMessage.trim() || chatSending) return;

    const userMsg = chatMessage.trim();
    setChatMessage("");
    setChatSending(true);
    setChatMessages((prev) => [...prev, { role: "user", content: userMsg }]);

    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trip_plan_id: id,
          message: userMsg,
        }),
      });

      if (!res.ok) throw new Error("Chat modification failed");
      const data = await res.json();

      // Save updated itinerary to Prisma
      if (data.updated_itinerary) {
        try {
          const updatedParsed =
            typeof data.updated_itinerary === "string"
              ? JSON.parse(data.updated_itinerary)
              : data.updated_itinerary;
          await fetch(`/api/trips/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              itinerary: updatedParsed.itinerary || updatedParsed,
            }),
          });
        } catch {
          // Fallback
        }
      }

      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.message || "Itinerary updated!" },
      ]);

      // Refresh plan data
      fetchPlan();
    } catch {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong." },
      ]);
    } finally {
      setChatSending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-10 h-10 mx-auto text-red-400 mb-3" />
          <h3 className="text-lg font-semibold">Trip not found</h3>
        </div>
      </div>
    );
  }

  // Robustly parse JSON fields that might be strings or objects
  const parseJsonField = (val: unknown): Record<string, unknown> | null => {
    if (!val) return null;
    if (typeof val === "string") {
      try { return JSON.parse(val); } catch { return null; }
    }
    if (typeof val === "object") return val as Record<string, unknown>;
    return null;
  };

  const itinerary = parseJsonField(plan.itinerary);
  const rawResponses = parseJsonField(plan.raw_responses);

  const isProcessing =
    plan.status === "pending" || plan.status === "processing";
  const isCompleted = plan.status === "completed";

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-gradient-to-br from-emerald-50/30 via-background to-teal-50/30">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">
              {plan.name || plan.destination || "Your Trip"}
            </h1>
            <div className="flex items-center gap-2 text-muted-foreground text-sm mt-1">
              <MapPin className="w-3.5 h-3.5" /> {plan.destination}
              {plan.duration > 0 && (
                <>
                  <span>•</span>
                  <Calendar className="w-3.5 h-3.5" /> {plan.duration} days
                </>
              )}
            </div>
          </div>

          {isCompleted && (
            <Button
              onClick={() => setChatOpen(!chatOpen)}
              className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white"
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              {chatOpen ? "Close Chat" : "Modify Trip"}
            </Button>
          )}
        </div>

        {/* Status Tracker - shown while processing */}
        {isProcessing && (
          <Card className="mb-6 border-0 shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <Loader2 className="w-5 h-5 animate-spin text-emerald-500" />
                <h3 className="font-semibold">Generating Your Trip...</h3>
              </div>
              <div className="space-y-3">
                {STEPS.map((step, i) => {
                  const currentStepIndex = STEPS.findIndex(
                    (s) =>
                      plan.current_step?.toLowerCase().includes(s.toLowerCase().split(" ")[0])
                  );
                  const isDone = i < currentStepIndex;
                  const isCurrent = i === currentStepIndex;

                  return (
                    <div key={step} className="flex items-center gap-3">
                      {isDone ? (
                        <CheckCircle className="w-5 h-5 text-emerald-500" />
                      ) : isCurrent ? (
                        <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                      ) : (
                        <Clock className="w-5 h-5 text-muted-foreground/30" />
                      )}
                      <span
                        className={
                          isDone
                            ? "text-emerald-700 font-medium"
                            : isCurrent
                            ? "text-blue-700 font-medium"
                            : "text-muted-foreground"
                        }
                      >
                        {step}
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Failed state */}
        {plan.status === "failed" && (
          <Card className="mb-6 border-red-200 bg-red-50">
            <CardContent className="p-6 text-center">
              <AlertCircle className="w-10 h-10 mx-auto text-red-400 mb-3" />
              <h3 className="font-semibold text-red-700 mb-2">
                Generation Failed
              </h3>
              <p className="text-red-600 text-sm">{plan.error || "An error occurred. Please try again."}</p>
            </CardContent>
          </Card>
        )}

        {/* Main content area with optional chat panel */}
        <div className={`flex gap-6 ${chatOpen ? "flex-col lg:flex-row" : ""}`}>
          {/* Itinerary content */}
          <div className={chatOpen ? "flex-1 min-w-0" : "w-full"}>
            {isCompleted && itinerary && (
              <Tabs defaultValue="itinerary">
                <TabsList className="w-full grid grid-cols-5 mb-4">
                  <TabsTrigger value="itinerary" className="gap-1.5 text-xs sm:text-sm">
                    <Calendar className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Itinerary</span>
                  </TabsTrigger>
                  <TabsTrigger value="hotels" className="gap-1.5 text-xs sm:text-sm">
                    <Hotel className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Hotels</span>
                  </TabsTrigger>
                  <TabsTrigger value="food" className="gap-1.5 text-xs sm:text-sm">
                    <UtensilsCrossed className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Food</span>
                  </TabsTrigger>
                  <TabsTrigger value="places" className="gap-1.5 text-xs sm:text-sm">
                    <MapPin className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Places</span>
                  </TabsTrigger>
                  <TabsTrigger value="budget" className="gap-1.5 text-xs sm:text-sm">
                    <Wallet className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Budget</span>
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="itinerary">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Calendar className="w-5 h-5 text-emerald-500" />
                        Day-by-Day Itinerary
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {itinerary && Array.isArray((itinerary as Record<string, unknown>).day_by_day_plan) && ((itinerary as Record<string, unknown>).day_by_day_plan as unknown[]).length > 0 ? (
                        <div className="space-y-6">
                          {((itinerary as Record<string, unknown>)
                            .day_by_day_plan as Array<Record<string, unknown>>
                          ).map((day, i) => (
                            <div key={i}>
                              <h3 className="font-bold text-lg text-emerald-700 mb-3">
                                Day {(day.day as number) || i + 1}{day.date ? `: ${day.date}` : ""}{day.title ? ` — ${day.title}` : ""}
                              </h3>
                              {/* New format: morning/afternoon/evening */}
                              {!!(day.morning || day.afternoon || day.evening) ? (
                                <div className="space-y-3 ml-4">
                                  {!!day.morning && (
                                    <div className="flex gap-3 p-2 rounded-lg hover:bg-muted/50">
                                      <span className="text-xs font-mono text-amber-600 w-16 shrink-0 pt-0.5 font-semibold">Morning</span>
                                      <p className="text-sm">{String(day.morning)}</p>
                                    </div>
                                  )}
                                  {!!day.afternoon && (
                                    <div className="flex gap-3 p-2 rounded-lg hover:bg-muted/50">
                                      <span className="text-xs font-mono text-blue-600 w-16 shrink-0 pt-0.5 font-semibold">Afternoon</span>
                                      <p className="text-sm">{String(day.afternoon)}</p>
                                    </div>
                                  )}
                                  {!!day.evening && (
                                    <div className="flex gap-3 p-2 rounded-lg hover:bg-muted/50">
                                      <span className="text-xs font-mono text-purple-600 w-16 shrink-0 pt-0.5 font-semibold">Evening</span>
                                      <p className="text-sm">{String(day.evening)}</p>
                                    </div>
                                  )}
                                  {!!day.notes && (
                                    <p className="text-xs text-muted-foreground italic ml-2">💡 {String(day.notes)}</p>
                                  )}
                                </div>
                              ) : Array.isArray(day.activities) ? (
                                <div className="space-y-2 ml-4">
                                  {(day.activities as Array<Record<string, string>>).map(
                                    (act, j) => (
                                      <div
                                        key={j}
                                        className="flex gap-3 p-2 rounded-lg hover:bg-muted/50"
                                      >
                                        <span className="text-xs font-mono text-muted-foreground w-14 shrink-0 pt-0.5">
                                          {act.time || ""}
                                        </span>
                                        <div>
                                          <span className="font-medium">
                                            {act.activity || act.name || ""}
                                          </span>
                                          {act.description && (
                                            <p className="text-sm text-muted-foreground">
                                              {act.description}
                                            </p>
                                          )}
                                        </div>
                                      </div>
                                    )
                                  )}
                                </div>
                              ) : (
                                <p className="text-sm text-muted-foreground ml-4">
                                  {JSON.stringify(day)}
                                </p>
                              )}
                              {i < ((itinerary as Record<string, unknown>).day_by_day_plan as unknown[]).length - 1 && (
                                <Separator className="mt-4" />
                              )}
                            </div>
                          ))}
                        </div>
                      ) : rawResponses ? (
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown>
                            {(rawResponses as Record<string, string>).itinerary_agent || "No itinerary data available"}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-muted-foreground">No itinerary data available</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="hotels">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Hotel className="w-5 h-5 text-emerald-500" />
                        Hotels
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {Array.isArray((itinerary as Record<string, unknown>).hotels) ? (
                        <div className="space-y-4">
                          {((itinerary as Record<string, unknown>).hotels as Array<Record<string, string>>).map(
                            (hotel, i) => (
                              <div key={i} className="p-4 rounded-lg border">
                                <h4 className="font-semibold">{hotel.hotel_name || hotel.name}</h4>
                                <div className="flex gap-2 mt-1">
                                  {(hotel.price || hotel.price_range) && (
                                    <Badge className="bg-emerald-100 text-emerald-700 border-0">{hotel.price || hotel.price_range}</Badge>
                                  )}
                                  {hotel.rating && (
                                    <Badge variant="outline">⭐ {hotel.rating}</Badge>
                                  )}
                                </div>
                                {hotel.description && (
                                  <p className="text-sm text-muted-foreground mt-2">
                                    {hotel.description}
                                  </p>
                                )}
                              </div>
                            )
                          )}
                        </div>
                      ) : rawResponses ? (
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown>
                            {(rawResponses as Record<string, string>).hotel_agent || "No hotel data"}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-muted-foreground">No hotel data available</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="food">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <UtensilsCrossed className="w-5 h-5 text-emerald-500" />
                        Restaurants
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {Array.isArray((itinerary as Record<string, unknown>).restaurants) ? (
                        <div className="space-y-4">
                          {((itinerary as Record<string, unknown>).restaurants as Array<Record<string, string>>).map(
                            (rest, i) => (
                              <div key={i} className="p-4 rounded-lg border">
                                <h4 className="font-semibold">{rest.name}</h4>
                                {rest.cuisine && (
                                  <Badge variant="outline" className="mt-1">{rest.cuisine}</Badge>
                                )}
                                {rest.description && (
                                  <p className="text-sm text-muted-foreground mt-2">
                                    {rest.description}
                                  </p>
                                )}
                              </div>
                            )
                          )}
                        </div>
                      ) : rawResponses ? (
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown>
                            {(rawResponses as Record<string, string>).dining_agent || "No food data"}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-muted-foreground">No food data available</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="places">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <MapPin className="w-5 h-5 text-emerald-500" />
                        Attractions
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {Array.isArray((itinerary as Record<string, unknown>).attractions) ? (
                        <div className="space-y-4">
                          {((itinerary as Record<string, unknown>).attractions as Array<Record<string, string>>).map(
                            (place, i) => (
                              <div key={i} className="p-4 rounded-lg border">
                                <h4 className="font-semibold">{place.name}</h4>
                                {place.description && (
                                  <p className="text-sm text-muted-foreground mt-2">
                                    {place.description}
                                  </p>
                                )}
                              </div>
                            )
                          )}
                        </div>
                      ) : rawResponses ? (
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown>
                            {(rawResponses as Record<string, string>).destination_agent || "No places data"}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-muted-foreground">No places data available</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="budget">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Wallet className="w-5 h-5 text-emerald-500" />
                        Budget Breakdown
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {itinerary && (!!(itinerary as Record<string, unknown>).budget_summary || !!(itinerary as Record<string, unknown>).total_estimated_cost) ? (
                        <div className="space-y-4">
                          {!!(itinerary as Record<string, unknown>).total_estimated_cost && (
                            <div className="p-4 bg-emerald-50 rounded-lg">
                              <Sparkles className="w-5 h-5 text-emerald-600 mb-2" />
                              <p className="text-2xl font-bold text-emerald-700">
                                {String((itinerary as Record<string, unknown>).total_estimated_cost)}
                              </p>
                              <p className="text-sm text-emerald-600">
                                Estimated Total Cost
                              </p>
                            </div>
                          )}
                          {!!(itinerary as Record<string, unknown>).budget_summary && (
                            <div className="prose prose-sm max-w-none">
                              <ReactMarkdown>
                                {String((itinerary as Record<string, unknown>).budget_summary)}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                      ) : rawResponses ? (
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown>
                            {String((rawResponses as Record<string, string>).budget_agent || "No budget data")}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-muted-foreground">No budget data available</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            )}
          </div>

          {/* Chat Panel */}
          {chatOpen && (
            <div className="w-full lg:w-96 shrink-0">
              <Card className="h-[600px] flex flex-col">
                <CardHeader className="flex flex-row items-center justify-between py-3 px-4 border-b">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-emerald-500" />
                    Modify Your Trip
                  </CardTitle>
                  <button onClick={() => setChatOpen(false)}>
                    <X className="w-4 h-4 text-muted-foreground" />
                  </button>
                </CardHeader>
                <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
                  {chatMessages.length === 0 && (
                    <p className="text-sm text-muted-foreground text-center pt-8">
                      Ask the AI to modify your itinerary!<br />
                      <span className="text-xs">
                        e.g. &quot;Add more nightlife&quot; or &quot;Make it cheaper&quot;
                      </span>
                    </p>
                  )}
                  {chatMessages.map((msg, i) => (
                    <div
                      key={i}
                      className={`text-sm p-3 rounded-lg max-w-[85%] ${
                        msg.role === "user"
                          ? "bg-emerald-500 text-white ml-auto"
                          : "bg-muted"
                      }`}
                    >
                      {msg.content}
                    </div>
                  ))}
                  {chatSending && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="w-3 h-3 animate-spin" /> Updating
                      itinerary...
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </CardContent>
                <div className="p-3 border-t flex gap-2">
                  <Input
                    placeholder="Type a modification..."
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleChatSend()}
                    disabled={chatSending}
                    className="h-10"
                  />
                  <Button
                    size="sm"
                    onClick={handleChatSend}
                    disabled={!chatMessage.trim() || chatSending}
                    className="h-10 bg-emerald-500 hover:bg-emerald-600"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
