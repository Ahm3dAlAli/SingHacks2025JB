import { NextResponse } from "next/server";
import { listSuggestions } from "@/lib/mock/suggestions";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const status = (url.searchParams.get("status") as any) || undefined;
  const updateId = url.searchParams.get("updateId") || undefined;
  let items = listSuggestions({ status });
  if (updateId) items = items.filter((s) => s.updateId === updateId);
  return NextResponse.json({ items });
}
