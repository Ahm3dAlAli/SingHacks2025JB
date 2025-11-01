import { NextResponse } from "next/server";

type TuneBody = {
  signals?: { name: string; outcome: "approve" | "escalate" | "hold" }[];
};

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as TuneBody;
  // Very simple proposal: increase weight for signals tied to escalations; decrease for approves.
  const proposals = (body.signals ?? []).map((s) => ({
    signal: s.name,
    weightDelta: s.outcome === "escalate" ? +0.2 : s.outcome === "approve" ? -0.1 : 0,
    thresholdDelta: s.outcome === "escalate" ? -2 : s.outcome === "approve" ? +1 : 0,
  }));
  return NextResponse.json({ ok: true, proposals });
}

