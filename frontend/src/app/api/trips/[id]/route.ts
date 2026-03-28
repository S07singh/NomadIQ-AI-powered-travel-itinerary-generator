import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

// GET /api/trips/[id] — Get single trip details
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;

  const trip = await prisma.tripPlan.findFirst({
    where: { id, userId: session.user.id },
    include: {
      chatMessages: {
        orderBy: { createdAt: "asc" },
      },
    },
  });

  if (!trip) {
    return NextResponse.json({ error: "Trip not found" }, { status: 404 });
  }

  return NextResponse.json({
    success: true,
    trip_plan_id: trip.id,
    status: trip.status,
    current_step: trip.currentStep,
    itinerary: trip.itinerary,
    raw_responses: trip.rawResponses,
    error: trip.error,
    name: trip.name,
    destination: trip.destination,
    duration: trip.duration,
    created_at: trip.createdAt.toISOString(),
    chat_messages: trip.chatMessages.map((m) => ({
      role: m.role,
      content: m.content,
      created_at: m.createdAt.toISOString(),
    })),
  });
}

// PUT /api/trips/[id] — Update a trip
export async function PUT(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;
  const body = await req.json();

  // Verify ownership
  const existing = await prisma.tripPlan.findFirst({
    where: { id, userId: session.user.id },
  });

  if (!existing) {
    return NextResponse.json({ error: "Trip not found" }, { status: 404 });
  }

  const trip = await prisma.tripPlan.update({
    where: { id },
    data: {
      name: body.name ?? existing.name,
      destination: body.destination ?? existing.destination,
      duration: body.duration ?? existing.duration,
      status: body.status ?? existing.status,
      currentStep: body.current_step ?? existing.currentStep,
      itinerary: body.itinerary ?? existing.itinerary,
      rawResponses: body.raw_responses ?? existing.rawResponses,
      error: body.error ?? existing.error,
      travelStyle: body.travel_style ?? existing.travelStyle,
      budget: body.budget ?? existing.budget,
    },
  });

  return NextResponse.json({ success: true, trip });
}

// DELETE /api/trips/[id] — Delete a trip
export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;

  // Verify ownership
  const existing = await prisma.tripPlan.findFirst({
    where: { id, userId: session.user.id },
  });

  if (!existing) {
    return NextResponse.json({ error: "Trip not found" }, { status: 404 });
  }

  await prisma.tripPlan.delete({ where: { id } });

  return NextResponse.json({ success: true, message: "Trip deleted" });
}
