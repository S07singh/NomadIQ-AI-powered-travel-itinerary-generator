import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

// GET /api/trips — List all trips for the logged-in user
export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const trips = await prisma.tripPlan.findMany({
    where: { userId: session.user.id },
    orderBy: { createdAt: "desc" },
    select: {
      id: true,
      name: true,
      destination: true,
      duration: true,
      status: true,
      currentStep: true,
      travelStyle: true,
      budget: true,
      budgetCurrency: true,
      createdAt: true,
    },
  });

  return NextResponse.json({ success: true, plans: trips });
}

// POST /api/trips — Create a new trip plan
export async function POST(req: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();

  const trip = await prisma.tripPlan.create({
    data: {
      userId: session.user.id,
      name: body.name || `Trip to ${body.destination}`,
      destination: body.destination,
      startingLocation: body.starting_location || "",
      travelDatesStart: body.travel_dates?.start || "",
      travelDatesEnd: body.travel_dates?.end || "",
      duration: body.duration || 3,
      travelingWith: body.traveling_with || "Solo",
      adults: body.adults || 1,
      children: body.children || 0,
      budget: body.budget || 1000,
      budgetCurrency: body.budget_currency || "USD",
      travelStyle: body.travel_style || "comfort",
      vibes: body.vibes || [],
      interests: body.interests || "",
      additionalInfo: body.additional_info || "",
      status: "pending",
    },
  });

  return NextResponse.json({
    success: true,
    trip_plan_id: trip.id,
  });
}
