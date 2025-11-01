import { NextResponse } from "next/server";

type LoginBody = {
  email?: string;
  password?: string;
};

export async function POST(request: Request) {
  const body = (await request.json()) as LoginBody;
  const email = (body.email || "").trim();
  const password = body.password || "";

  // Very simple mock validation
  const valid = email.includes("@") && password.length >= 6;

  if (!valid) {
    return NextResponse.json({ ok: false, error: "Invalid credentials" }, { status: 401 });
  }

  function determineRole(e: string): "relationship_manager" | "compliance_manager" | "legal" {
    const lower = e.toLowerCase();
    if (lower.startsWith("legal@") || lower.includes("+legal")) return "legal";
    if (lower.startsWith("compliance@") || lower.includes("+compliance")) return "compliance_manager";
    return "relationship_manager";
  }
  const token = `dev-${Math.random().toString(36).slice(2)}`;
  const role = determineRole(email);
  return NextResponse.json({ ok: true, token, role });
}
