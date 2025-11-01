import { NextResponse } from "next/server";
import { compileRuleset } from "@/lib/mock/rules";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  return NextResponse.json(compileRuleset(body));
}

