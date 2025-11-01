import { NextResponse } from "next/server";
import { evaluateTx } from "@/lib/mock/transactions";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const result = evaluateTx(body || {});
  return NextResponse.json(result);
}

