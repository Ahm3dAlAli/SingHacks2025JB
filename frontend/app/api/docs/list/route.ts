import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export async function GET() {
  const dir = path.join(process.cwd(), "docs");
  let files: string[] = [];
  try {
    files = await fs.readdir(dir);
  } catch {
    return NextResponse.json({ items: [] });
  }
  const items = await Promise.all(
    files
      .filter((f) => f.endsWith(".md"))
      .map(async (f) => {
        const p = path.join(dir, f);
        const text = await fs.readFile(p, "utf8").catch(() => "");
        const firstLine = (text.split(/\r?\n/)[0] || "").replace(/^#\s*/, "").trim();
        const slug = f.replace(/\.md$/, "");
        return { slug, file: f, title: firstLine || slug };
      })
  );
  items.sort((a, b) => a.title.localeCompare(b.title));
  return NextResponse.json({ items });
}

