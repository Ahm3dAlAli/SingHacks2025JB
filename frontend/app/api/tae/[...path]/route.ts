import { NextResponse } from "next/server";

type Ctx = { params: Promise<{ path?: string[] }> };

const BASE = process.env.NEXT_PUBLIC_TAE_API_URL || "http://localhost:8002";

async function proxy(request: Request, ctx: Ctx) {
  try {
    const { path = [] } = await ctx.params;
    const url = new URL(request.url);
    const target = new URL(path.join("/"), BASE);
    target.search = url.search;

    const headers = new Headers(request.headers);
    headers.delete("host");

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
      { error: "TAE service unavailable", detail: err?.message || String(err) },
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

