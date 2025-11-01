import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  // Accept any feedback payload and echo back.
  return NextResponse.json({ ok: true, received: body, stored: true });
}

