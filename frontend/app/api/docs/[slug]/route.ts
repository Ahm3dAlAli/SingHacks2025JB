import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export async function GET(_: Request, ctx: { params: Promise<{ slug: string }> }) {
  const { slug } = await ctx.params;
  const safe = slug.replace(/[^a-z0-9-_]/gi, "");
  if (!safe) return NextResponse.json({ error: "Invalid" }, { status: 400 });
  const p = path.join(process.cwd(), "docs", `${safe}.md`);
  try {
    const text = await fs.readFile(p, "utf8");
    return NextResponse.json({ slug: safe, content: text });
  } catch {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
}

