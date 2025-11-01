import { NextResponse } from "next/server";
import { listRules } from "@/lib/mock/rules";

export async function GET() {
  return NextResponse.json({ items: listRules() });
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const id = `rule-${Date.now()}`;
  return NextResponse.json({ id, name: body.name ?? "New Rule", status: "inactive", versionId: `v-${id}-0`, dsl: body.dsl ?? "", createdAt: new Date().toISOString() });
}

