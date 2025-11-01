import { NextResponse } from "next/server";

type Feedback = {
  id: string;
  decision: string; // e.g., approve | hold | escalate | reject | override
  reason?: string;
};

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as Feedback;
  return NextResponse.json({ ok: true, received: body, tracked: true });
}
