import { NextResponse } from "next/server";
import { listAlerts, generateAlertDetail } from "@/lib/mock/alerts";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const severity = url.searchParams.get("severity") as any;
  const status = url.searchParams.get("status") as any;
  const entity = url.searchParams.get("entity") ?? undefined;
  const data = listAlerts({ severity, status, entity });
  return NextResponse.json({ items: data });
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const id = `mock-${Date.now()}`;
  const detail = generateAlertDetail(id);
  const merged = {
    ...detail,
    severity: body.severity ?? detail.severity,
    status: body.status ?? detail.status,
    entity: body.entity ?? detail.entity,
  };
  return NextResponse.json(merged, { status: 201 });
}

