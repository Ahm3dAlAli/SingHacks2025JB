import { NextResponse } from "next/server";
import { listForRole, type AppRole } from "@/lib/server/docsStore";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const role = (url.searchParams.get("role") as AppRole) || "relationship_manager";
  const items = listForRole(role);
  return NextResponse.json({ items });
}

