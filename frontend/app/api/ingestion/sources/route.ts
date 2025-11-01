import { NextResponse } from "next/server";
import { listSources } from "@/lib/mock/ingestion";

export async function GET() {
  return NextResponse.json({ items: listSources() });
}

