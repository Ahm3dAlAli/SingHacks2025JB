import { NextResponse } from "next/server";
import { promoteArtifact } from "@/lib/mock/rules";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  return NextResponse.json(promoteArtifact(body));
}

