import { NextResponse } from "next/server";
import { createItem } from "@/lib/server/docsStore";

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const file = form.get("file") as File | null;
    const title = (form.get("title") as string) || "";
    const entityId = (form.get("entityId") as string) || null;
    const role = ((form.get("role") as string) || "relationship_manager") as any;
    if (!file) return NextResponse.json({ error: "Missing file" }, { status: 400 });
    const arrayBuf = await file.arrayBuffer();
    const buf = Buffer.from(arrayBuf);
    const item = await createItem({
      title,
      entityId,
      uploadedBy: role,
      fileName: (file as any).name || title || "upload.bin",
      mimeType: file.type || "application/octet-stream",
      data: buf,
    });
    return NextResponse.json({ ok: true, item });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message || "Upload failed" }, { status: 500 });
  }
}

