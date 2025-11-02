import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export async function GET(_: Request, ctx: { params: Promise<{ file: string }> }) {
  const { file } = await ctx.params;
  const safe = file.replace(/[^a-zA-Z0-9._-]/g, "");
  if (!safe) return NextResponse.json({ error: "Invalid" }, { status: 400 });
  const p = path.join(process.cwd(), "public", "uploads", safe);
  try {
    const data = await fs.readFile(p);
    const ext = path.extname(safe).toLowerCase();
    const type =
      ext === ".png" ? "image/png" :
      ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" :
      ext === ".gif" ? "image/gif" :
      ext === ".pdf" ? "application/pdf" :
      ext === ".docx" ? "application/vnd.openxmlformats-officedocument.wordprocessingml.document" :
      ext === ".txt" ? "text/plain; charset=utf-8" :
      "application/octet-stream";
    return new Response(data, { headers: { "Content-Type": type } });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message || "Not found" }, { status: 404 });
  }
}
