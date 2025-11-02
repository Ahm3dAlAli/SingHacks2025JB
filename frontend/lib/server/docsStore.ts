import { promises as fs } from "fs";
import path from "path";

export type AppRole = "relationship_manager" | "compliance_manager" | "legal";
export type DocStatus = "pending_compliance" | "pending_legal" | "approved" | "rejected";

export type ReviewDoc = {
  id: string;
  title: string;
  entityId?: string | null;
  uploadedAt: string; // ISO
  uploadedBy: AppRole;
  filePath: string; // public path e.g. /uploads/abc.jpg
  mimeType: string;
  flags: string[];
  status: DocStatus;
  notes: { at: string; by: AppRole; action: string; note?: string }[];
};

const items: ReviewDoc[] = [];
const uploadDir = path.join(process.cwd(), "public", "uploads");

export async function ensureUploadDir() {
  try {
    await fs.mkdir(uploadDir, { recursive: true });
  } catch {}
}

export function listForRole(role: AppRole): ReviewDoc[] {
  if (role === "relationship_manager") {
    // RMs see all items for now; could filter by entityId
    return items.slice().sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime());
  }
  if (role === "compliance_manager") {
    return items.filter((i) => i.status === "pending_compliance").sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime());
  }
  if (role === "legal") {
    return items.filter((i) => i.status === "pending_legal").sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime());
  }
  return [];
}

export function getById(id: string): ReviewDoc | undefined {
  return items.find((i) => i.id === id);
}

export function listByEntity(entityId: string): ReviewDoc[] {
  return items.filter((i) => (i.entityId || "") === entityId).sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime());
}

export async function createItem(params: {
  title: string;
  entityId?: string | null;
  uploadedBy: AppRole;
  fileName: string;
  mimeType: string;
  data: Buffer;
}): Promise<ReviewDoc> {
  await ensureUploadDir();
  const id = Math.random().toString(36).slice(2, 10);
  const ext = path.extname(params.fileName) || inferExt(params.mimeType) || ".bin";
  const fileBase = `${id}${ext}`;
  const diskPath = path.join(uploadDir, fileBase);
  await fs.writeFile(diskPath, params.data);
  // Use API route to serve uploads to avoid static serving issues in standalone runtime
  const publicPath = `/api/uploads/${fileBase}`;
  const flags = deriveFlags(params.fileName, params.mimeType);
  const item: ReviewDoc = {
    id,
    title: params.title || params.fileName,
    entityId: params.entityId ?? null,
    uploadedAt: new Date().toISOString(),
    uploadedBy: params.uploadedBy,
    filePath: publicPath,
    mimeType: params.mimeType,
    flags,
    status: "pending_compliance",
    notes: [{ at: new Date().toISOString(), by: params.uploadedBy, action: "upload" }],
  };
  items.unshift(item);
  return item;
}

export function decide(id: string, by: AppRole, action: "approve" | "reject" | "escalate", note?: string, fraud?: boolean): ReviewDoc | undefined {
  const item = getById(id);
  if (!item) return undefined;
  if (action === "approve") item.status = "approved";
  else if (action === "reject") item.status = "rejected";
  else if (action === "escalate") item.status = "pending_legal";
  item.notes.push({ at: new Date().toISOString(), by, action, note });
  if (fraud) {
    if (!item.flags.includes("Fraud suspected")) item.flags.push("Fraud suspected");
  }
  return item;
}

function inferExt(mime: string): string | null {
  if (mime.includes("png")) return ".png";
  if (mime.includes("jpeg")) return ".jpg";
  if (mime.includes("jpg")) return ".jpg";
  if (mime.includes("gif")) return ".gif";
  if (mime.includes("pdf")) return ".pdf";
  return null;
}

function deriveFlags(fileName: string, mime: string): string[] {
  const f = fileName.toLowerCase();
  const out: string[] = [];
  if (f.includes("house") || f.includes("property")) out.push("Property purchase detected");
  if (mime.includes("image/")) out.push("Image scanned");
  if (mime.includes("pdf")) out.push("PDF scanned");
  // Mock reverse image search: if name hints at brand/chain, flag
  if (f.includes("airbnb") || f.includes("uber")) out.push("Possible consumer-platform receipt");
  return out;
}
