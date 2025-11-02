import { NextResponse } from "next/server";

type Ctx = { params: Promise<{ path?: string[] }> };

// DCE v2 base URL (prefer server-side env); default to 8010
const BASE =
  process.env.CORROBORATION_API_URL ||
  process.env.NEXT_PUBLIC_DCE_API_URL ||
  process.env.NEXT_PUBLIC_CORROBORATION_API_URL ||
  "http://localhost:8010";

// v2: "/health" is at root; API methods under "/api/v1"
const PREFIX = (process.env.CORROBORATION_API_PREFIX || "/api/v1").trim();
const API_KEY = process.env.CORROBORATION_API_KEY;

async function proxy(request: Request, ctx: Ctx) {
  try {
    const { path = [] } = await ctx.params;
    const url = new URL(request.url);

    const first = (path[0] || "").toLowerCase();
    const mapped = path.join("/");
    const needsPrefix = PREFIX && first !== "health";
    const pref = needsPrefix ? `${PREFIX.replace(/\/$/, "")}/` : "";
    const target = new URL(`${pref}${mapped}` || pref, BASE);
    target.search = url.search;

    const headers = new Headers(request.headers);
    headers.delete("host");
    if (API_KEY && !headers.has("authorization")) headers.set("authorization", `Bearer ${API_KEY}`);

    const method = request.method.toUpperCase();
    const hasBody = !["GET", "HEAD"].includes(method);
    const body = hasBody ? await request.arrayBuffer() : undefined;

    const resp = await fetch(target.toString(), {
      method,
      headers,
      body: hasBody ? Buffer.from(body!) : undefined,
      cache: "no-store" as any,
    });

    const respHeaders = new Headers(resp.headers);
    return new Response(resp.body, { status: resp.status, headers: respHeaders });
  } catch (err: any) {
    return NextResponse.json(
      { error: "Corroboration service unavailable", detail: err?.message || String(err) },
      { status: 502 }
    );
  }
}

export async function GET(req: Request, ctx: Ctx) { return proxy(req, ctx); }
export async function POST(req: Request, ctx: Ctx) { return proxy(req, ctx); }
export async function PUT(req: Request, ctx: Ctx) { return proxy(req, ctx); }
export async function PATCH(req: Request, ctx: Ctx) { return proxy(req, ctx); }
export async function DELETE(req: Request, ctx: Ctx) { return proxy(req, ctx); }
export async function HEAD(req: Request, ctx: Ctx) { return proxy(req, ctx); }
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  });
}
