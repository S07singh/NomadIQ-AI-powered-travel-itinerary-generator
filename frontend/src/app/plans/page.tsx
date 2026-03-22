"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Plane,
  MapPin,
  Calendar,
  Loader2,
  Plus,
  Clock,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

interface TripPlan {
  id: string;
  name: string;
  destination: string;
  duration: number;
  created_at: string;
  status: string;
  current_step: string | null;
}

export default function PlansPage() {
  const [plans, setPlans] = useState<TripPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/plans");
        if (!res.ok) throw new Error(`Failed to fetch: ${res.status}`);
        const data = await res.json();
        console.log("Plans API response:", data);
        setPlans(data.plans || []);
      } catch (err) {
        console.error("Error fetching plans:", err);
        setError("Could not connect to backend. Make sure it's running on port 8000.");
      } finally {
        setLoading(false);
      }
    };
    fetchPlans();
  }, []);

  const statusConfig: Record<string, { label: string; color: string; icon: typeof Clock }> = {
    pending: { label: "Pending", color: "bg-amber-100 text-amber-700", icon: Clock },
    processing: { label: "Processing", color: "bg-blue-100 text-blue-700", icon: Loader2 },
    completed: { label: "Completed", color: "bg-emerald-100 text-emerald-700", icon: CheckCircle },
    failed: { label: "Failed", color: "bg-red-100 text-red-700", icon: AlertCircle },
  };

  if (loading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-10 h-10 mx-auto text-red-400 mb-3" />
          <h3 className="text-lg font-semibold mb-2">Connection Error</h3>
          <p className="text-muted-foreground text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-gradient-to-br from-emerald-50/30 via-background to-teal-50/30">
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">My Trips</h1>
            <p className="text-muted-foreground">
              {plans.length} trip{plans.length !== 1 ? "s" : ""} planned
            </p>
          </div>
          <Link href="/plan">
            <Button className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white">
              <Plus className="w-4 h-4 mr-1.5" /> New Trip
            </Button>
          </Link>
        </div>

        {plans.length === 0 ? (
          <div className="text-center py-20">
            <Plane className="w-12 h-12 mx-auto text-muted-foreground/30 mb-4" />
            <h3 className="text-xl font-semibold mb-2">No trips yet</h3>
            <p className="text-muted-foreground mb-6">
              Start planning your first adventure with AI!
            </p>
            <Link href="/plan">
              <Button className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white">
                <Plus className="w-4 h-4 mr-1.5" /> Plan My First Trip
              </Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {plans.map((plan) => {
              const config = statusConfig[plan.status] || statusConfig.pending;
              const StatusIcon = config.icon;
              return (
                <Link key={plan.id} href={`/plan/${plan.id}`}>
                  <Card className="hover:shadow-lg transition-all cursor-pointer group border hover:border-emerald-300">
                    <CardContent className="p-5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                            <MapPin className="w-6 h-6 text-white" />
                          </div>
                          <div>
                            <h3 className="font-semibold text-lg">
                              {plan.name || plan.destination || "Untitled Trip"}
                            </h3>
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                              {plan.destination && (
                                <span className="flex items-center gap-1">
                                  <MapPin className="w-3 h-3" /> {plan.destination}
                                </span>
                              )}
                              {plan.duration > 0 && (
                                <span className="flex items-center gap-1">
                                  <Calendar className="w-3 h-3" /> {plan.duration} days
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="text-right flex items-center gap-3">
                          <Badge className={`${config.color} border-0`}>
                            <StatusIcon className={`w-3 h-3 mr-1 ${plan.status === "processing" ? "animate-spin" : ""}`} />
                            {config.label}
                          </Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
