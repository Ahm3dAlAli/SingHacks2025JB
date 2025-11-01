import { NextResponse } from "next/server";
import { listRegulatoryUpdates } from "@/lib/mock/regulatory";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const authority = url.searchParams.get("authority") ?? undefined;
  const q = url.searchParams.get("q") ?? undefined;
  const items = listRegulatoryUpdates({ authority, q });
  return NextResponse.json({ items });
}

