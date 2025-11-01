import { NextResponse } from "next/server";
import { mockAdverseMediaForName } from "@/lib/server/adverseMedia";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const name = searchParams.get("name");
  if (!name) return NextResponse.json({ error: "Missing name" }, { status: 400 });
  const data = mockAdverseMediaForName(name);
  return NextResponse.json({ name, ...data });
}

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const name = (body?.name || "").toString().trim();
    if (!name) return NextResponse.json({ error: "Missing name" }, { status: 400 });
    const data = mockAdverseMediaForName(name);
    return NextResponse.json({ name, ...data });
  } catch {
    return NextResponse.json({ error: "Bad request" }, { status: 400 });
  }
}

