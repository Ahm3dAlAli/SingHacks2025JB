"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRole } from "@/lib/use-role";
import { Permissions } from "@/lib/rbac";
import { isLoggedIn } from "@/lib/auth";

type ReviewDoc = {
  id: string;
  title: string;
  filePath: string;
  uploadedAt: string;
  uploadedBy: string;
  flags: string[];
  status: string;
  notes?: { at: string; by: string; action: string; note?: string }[];
};

export default function DocsReviewPage() {
  const router = useRouter();
  useEffect(() => { if (!isLoggedIn()) router.replace("/login"); }, [router]);
  const { role } = useRole();
  const [items, setItems] = useState<ReviewDoc[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [clients, setClients] = useState<{ id: string; name: string }[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [commentMap, setCommentMap] = useState<Record<string, string>>({});
  const [fraudMap, setFraudMap] = useState<Record<string, boolean>>({});

  async function load() {
    try {
      setError(null);
      const res = await fetch(`/api/docs/review?role=${role}`);
      const data = (await res.json()) as { items: ReviewDoc[] };
      setItems(data.items);
    } catch (e: any) {
      setError(e.message || "Error");
    }
  }

  useEffect(() => { load(); }, [role]);

  // Load clients for the picker
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/entities");
        if (!res.ok) return;
        const data = (await res.json()) as { items: { id: string; name: string }[] };
        setClients(data.items?.map((x) => ({ id: x.id, name: x.name })) ?? []);
      } catch {}
    })();
  }, []);

  async function onUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget; // capture before any await
    const form = new FormData(formEl);
    form.set("role", role);
    const file = form.get("file") as File | null;
    if (!file) return;
    setUploading(true);
    try {
      const res = await fetch("/api/docs/upload", { method: "POST", body: form });
      if (!res.ok) throw new Error("Upload failed");
      await load();
      formEl.reset();
      setFileName("");
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <div className="mb-4">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Documentation Review</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">Upload supporting documents and review flagged items.</p>
      </div>
      <div className="mb-3 flex items-center gap-3 text-xs">
        <label className="text-zinc-600 dark:text-zinc-400">Status</label>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded border bg-white p-1 dark:border-zinc-700 dark:bg-zinc-950">
          <option value="">All</option>
          <option value="pending_compliance">Pending — Compliance</option>
          <option value="pending_legal">Pending — Legal</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      {/* RM upload form */}
      {role === "relationship_manager" ? (
        <form onSubmit={onUpload} className="mb-4 flex flex-wrap items-end gap-3 rounded border p-3">
          <div className="flex flex-col">
            <label className="text-xs text-zinc-600 dark:text-zinc-400">Title</label>
            <input name="title" className="rounded border p-1 text-sm dark:border-zinc-700 dark:bg-zinc-950" placeholder="e.g., Purchase Agreement" />
          </div>
          <div className="flex flex-col">
            <label className="text-xs text-zinc-600 dark:text-zinc-400">Client (optional)</label>
            <input
              name="entityId"
              list="client-picker"
              className="rounded border p-1 text-sm dark:border-zinc-700 dark:bg-zinc-950"
              placeholder="Search client by name…"
            />
            <datalist id="client-picker">
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </datalist>
          </div>
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              name="file"
              type="file"
              accept="application/pdf,image/*"
              className="hidden"
              onChange={(e) => setFileName(e.target.files?.[0]?.name || "")}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="rounded border px-3 py-1.5 text-xs shadow-sm"
            >
              Choose File
            </button>
            <span className="max-w-[240px] truncate text-xs text-zinc-600 dark:text-zinc-400">{fileName || "No file selected"}</span>
          </div>
          <button
            disabled={uploading || !fileName}
            className="rounded bg-primary px-3 py-1.5 text-xs text-primary-foreground disabled:opacity-60"
          >
            {uploading ? "Uploading…" : "Upload"}
          </button>
        </form>
      ) : null}

      {/* Queue list */}
      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/40">{error}</div>
      ) : items.length === 0 ? (
        <div className="rounded border p-4 text-sm text-zinc-600 dark:text-zinc-400">No items.</div>
      ) : (
        <ul className="space-y-2">
          {items.filter((it) => !statusFilter || it.status === statusFilter).map((it) => (
            <li key={it.id} className="rounded border p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="font-medium">{it.title}</div>
                    <StatusBadge status={it.status} />
                  </div>
                  <div className="text-xs text-zinc-500">Uploaded {new Date(it.uploadedAt).toLocaleString("en-SG", { timeZone: "Asia/Singapore" })} • by {it.uploadedBy}</div>
                  {it.flags.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-2">
                      {it.flags.map((f, i) => <span key={i} className="rounded bg-amber-100 px-2 py-0.5 text-[10px] text-amber-700">{f}</span>)}
                    </div>
                  ) : null}
                  {it.notes && it.notes.length > 0 ? (
                    <div className="mt-2 rounded border bg-white/50 p-2 text-xs dark:border-zinc-800 dark:bg-zinc-900/40">
                      <div className="mb-1 font-medium">History</div>
                      <ul className="space-y-1">
                        {it.notes.map((n, i) => (
                          <li key={i} className="flex items-center justify-between">
                            <span>{n.action}{n.note ? ` — ${n.note}` : ""}</span>
                            <span className="text-zinc-500">{new Date(n.at).toLocaleString("en-SG", { timeZone: "Asia/Singapore" })} • {n.by}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
                <div className="flex items-center gap-2">
                  <a href={it.filePath} target="_blank" className="rounded border px-3 py-1.5 text-xs">Open</a>
                  {role === "compliance_manager" ? (
                    <>
                      <div className="flex items-center gap-2">
                        <input
                          value={commentMap[it.id] || ""}
                          onChange={(e) => setCommentMap((m) => ({ ...m, [it.id]: e.target.value }))}
                          placeholder="Add comment"
                          className="w-40 rounded border p-1 text-xs dark:border-zinc-700 dark:bg-zinc-950"
                        />
                        <label className="flex items-center gap-1 text-[11px] text-zinc-600 dark:text-zinc-400">
                          <input type="checkbox" checked={!!fraudMap[it.id]} onChange={(e) => setFraudMap((m) => ({ ...m, [it.id]: e.target.checked }))} />
                          Flag as fraud
                        </label>
                      </div>
                      <Action id={it.id} action="approve" onDone={() => { load(); setCommentMap((m) => ({ ...m, [it.id]: "" })); }} note={commentMap[it.id] || ""} />
                      <Action id={it.id} action="reject" onDone={() => { load(); setCommentMap((m) => ({ ...m, [it.id]: "" })); }} note={commentMap[it.id] || ""} />
                      <Action id={it.id} action="escalate" onDone={() => { load(); setCommentMap((m) => ({ ...m, [it.id]: "" })); setFraudMap((m) => ({ ...m, [it.id]: false })); }} note={commentMap[it.id] || ""} fraud={!!fraudMap[it.id]}>Escalate</Action>
                    </>
                  ) : null}
                  {role === "legal" ? (
                    <>
                      <div className="flex items-center gap-2">
                        <input
                          value={commentMap[it.id] || ""}
                          onChange={(e) => setCommentMap((m) => ({ ...m, [it.id]: e.target.value }))}
                          placeholder="Add comment"
                          className="w-40 rounded border p-1 text-xs dark:border-zinc-700 dark:bg-zinc-950"
                        />
                      </div>
                      <Action id={it.id} action="approve" onDone={() => { load(); setCommentMap((m) => ({ ...m, [it.id]: "" })); }} note={commentMap[it.id] || ""} />
                      <Action id={it.id} action="reject" onDone={() => { load(); setCommentMap((m) => ({ ...m, [it.id]: "" })); }} note={commentMap[it.id] || ""} />
                    </>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Action({ id, action, onDone, children, note, fraud }: { id: string; action: "approve" | "reject" | "escalate"; onDone: () => void; children?: React.ReactNode; note?: string; fraud?: boolean }) {
  const { role } = useRole();
  async function go() {
    await fetch(`/api/docs/items/${id}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, role, note: note || undefined, fraud: !!fraud }) });
    onDone();
  }
  const label = children || action[0].toUpperCase() + action.slice(1);
  return <button onClick={go} className="rounded border px-3 py-1.5 text-xs">{label}</button>;
}

function StatusBadge({ status }: { status: string }) {
  const m: Record<string, { text: string; cls: string }> = {
    pending_compliance: { text: "Pending — Compliance", cls: "bg-amber-100 text-amber-700" },
    pending_legal: { text: "Pending — Legal", cls: "bg-orange-100 text-orange-700" },
    approved: { text: "Approved", cls: "bg-emerald-100 text-emerald-700" },
    rejected: { text: "Rejected", cls: "bg-red-100 text-red-700" },
  };
  const v = m[status] || { text: status, cls: "bg-zinc-100 text-zinc-700" };
  return <span className={`rounded px-2 py-0.5 text-[10px] ${v.cls}`}>{v.text}</span>;
}
