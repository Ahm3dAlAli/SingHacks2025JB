import { NextResponse } from "next/server";
import { listItems } from "@/lib/mock/ingestion";

export async function GET() {
  return NextResponse.json({ items: listItems() });
}

