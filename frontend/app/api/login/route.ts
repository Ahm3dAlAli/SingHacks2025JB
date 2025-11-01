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

  const token = `dev-${Math.random().toString(36).slice(2)}`;
  return NextResponse.json({ ok: true, token });
}

