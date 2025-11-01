import { NextResponse } from "next/server";
import { listPeople } from "@/lib/mock/entities";

export async function GET() {
  return NextResponse.json({ items: listPeople() });
}

