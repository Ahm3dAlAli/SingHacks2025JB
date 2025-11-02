"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRole } from "@/lib/use-role";
import { Permissions } from "@/lib/rbac";
import { isLoggedIn } from "@/lib/auth";
import {
  corroborateUpload,
  getStatistics,
  type CorroborationStats,
} from "@/lib/api/corroboration";

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
  const [stats, setStats] = useState<CorroborationStats | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);

  // Map internal doc id -> corroboration doc id
  const [corroMap, setCorroMap] = useState<Record<string, string>>({});
  const [analysisOpen, setAnalysisOpen] = useState<Record<string, boolean>>({});
  const [analysis, setAnalysis] = useState<Record<string, { loading: boolean; error?: string; doc?: any; risks?: any; text?: string; structure?: any }>>({});

  useEffect(() => {
    try {
      if (typeof window !== "undefined") {
        const raw = window.localStorage.getItem("corroMap");
        if (raw) setCorroMap(JSON.parse(raw));
      }
    } catch {}
  }, []);

  function saveCorroMap(next: Record<string, string>) {
    setCorroMap(next);
    try {
      if (typeof window !== "undefined") window.localStorage.setItem("corroMap", JSON.stringify(next));
    } catch {}
  }

  function extractDocId(resp: any): string | null {
    if (!resp) return null;
    return (
      resp.id ||
      resp.document_id ||
      resp.docId ||
      resp.document?.id ||
      resp.result?.id ||
      null
    );
  }

  async function sendToCorroboration(it: ReviewDoc) {
    try {
      // fetch the uploaded file from our static path and wrap as File
      // Try direct path first; if it fails and path starts with /uploads, use API fallback
      let r = await fetch(it.filePath);
      if (!r.ok && it.filePath.startsWith("/uploads/")) {
        r = await fetch(`/api${it.filePath}`);
      }
      if (!r.ok) throw new Error("Failed to fetch file");
      const blob = await r.blob();
      const name = it.title?.replace(/\s+/g, "-") || "document";
      const pathNoQuery = it.filePath.split("?")[0];
      const ext = (pathNoQuery.includes('.') ? `.${pathNoQuery.split('.').pop()}` : '').toLowerCase();
      const supported = [".pdf", ".docx", ".txt"];
      if (!supported.includes(ext)) throw new Error("Only PDF, DOCX, or TXT supported for corroboration");
      const primary = new File([blob], `${name}${ext}`, { type: blob.type || "application/octet-stream" });
      // choose up to 2 other items as references; fallback to duplicating primary
      const candidates = items.filter((x) => x.id !== it.id).slice(0, 2);
      const refs: File[] = [];
      for (const o of candidates) {
        let rr = await fetch(o.filePath);
        if (!rr.ok && o.filePath.startsWith("/uploads/")) rr = await fetch(`/api${o.filePath}`);
        if (rr.ok) {
          const b = await rr.blob();
          const n = o.title?.replace(/\s+/g, "-") || "reference";
          const p2 = o.filePath.split("?")[0];
          const ext2 = (p2.includes('.') ? `.${p2.split('.').pop()}` : '').toLowerCase();
          if (supported.includes(ext2)) {
            refs.push(new File([b], `${n}${ext2}`, { type: b.type || "application/octet-stream" }));
          }
        }
      }
      if (refs.length === 0) refs.push(new File([blob], `${name}${ext}`, { type: blob.type || "application/octet-stream" }));
      const result = await corroborateUpload(primary, refs);
      const next = { ...corroMap, [it.id]: "v2" };
      saveCorroMap(next);
      setAnalysis((m) => ({ ...m, [it.id]: { loading: false, doc: result } }));
      setAnalysisOpen((o) => ({ ...o, [it.id]: true }));
    } catch (e: any) {
      setError(e.message || "Failed to send to corroboration");
    }
  }

  async function refreshAnalysis(internalId: string) {
    const it = items.find((x) => x.id === internalId);
    if (!it) return;
    setAnalysis((m) => ({ ...m, [internalId]: { ...(m[internalId] || {}), loading: true, error: undefined } }));
    try {
      let r = await fetch(it.filePath);
      if (!r.ok && it.filePath.startsWith("/uploads/")) r = await fetch(`/api${it.filePath}`);
      if (!r.ok) throw new Error("Failed to fetch file");
      const blob = await r.blob();
      const name = it.title?.replace(/\s+/g, "-") || "document";
      const pathNoQuery2 = it.filePath.split("?")[0];
      const extMain = (pathNoQuery2.includes('.') ? `.${pathNoQuery2.split('.').pop()}` : '').toLowerCase();
      const supported2 = [".pdf", ".docx", ".txt"];
      if (!supported2.includes(extMain)) throw new Error("Only PDF, DOCX, or TXT supported for corroboration");
      const primary = new File([blob], `${name}${extMain}`, { type: blob.type || "application/octet-stream" });
      const candidates = items.filter((x) => x.id !== it.id).slice(0, 2);
      const refs: File[] = [];
      for (const o of candidates) {
        let rr = await fetch(o.filePath);
        if (!rr.ok && o.filePath.startsWith("/uploads/")) rr = await fetch(`/api${o.filePath}`);
        if (rr.ok) {
          const b = await rr.blob();
          const n = o.title?.replace(/\s+/g, "-") || "reference";
          const p2 = o.filePath.split("?")[0];
          const ext2 = (p2.includes('.') ? `.${p2.split('.').pop()}` : '').toLowerCase();
          if (supported2.includes(ext2)) {
            refs.push(new File([b], `${n}${ext2}`, { type: b.type || "application/octet-stream" }));
          }
        }
      }
      if (refs.length === 0) refs.push(new File([blob], `${name}${extMain}`, { type: blob.type || "application/octet-stream" }));
      const result = await corroborateUpload(primary, refs);
      setAnalysis((m) => ({ ...m, [internalId]: { loading: false, doc: result } }));
      setAnalysisOpen((o) => ({ ...o, [internalId]: true }));
    } catch (e: any) {
      setAnalysis((m) => ({ ...m, [internalId]: { loading: false, error: e.message || "Failed to load analysis" } }));
    }
  }

  async function loadStats() {
    try {
      setStatsError(null);
      const s = await getStatistics();
      setStats(s);
    } catch (e: any) {
      setStatsError(e.message || "Failed to load statistics");
    }
  }

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
      <div className="mb-3 flex flex-wrap items-center gap-3 text-xs">
        <label className="text-zinc-600 dark:text-zinc-400">Status</label>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded border bg-white p-1 dark:border-zinc-700 dark:bg-zinc-950">
          <option value="">All</option>
          <option value="pending_compliance">Pending — Compliance</option>
          <option value="pending_legal">Pending — Legal</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
        <button onClick={loadStats} className="rounded border px-2 py-1">Load Corroboration Stats</button>
        {statsError ? <span className="text-red-600">{statsError}</span> : null}
        {stats ? (
          <span className="rounded bg-zinc-100 px-2 py-0.5 text-[10px] text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200">
            Docs: {stats.total_documents} • High risk: {stats.total_high_risk}
          </span>
        ) : null}
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
                  {corroMap[it.id] ? (
                    <>
                      <button onClick={() => refreshAnalysis(it.id)} className="rounded border px-3 py-1.5 text-xs">{analysis[it.id]?.loading ? 'Refreshing…' : 'Refresh Analysis'}</button>
                      <button onClick={() => setAnalysisOpen((o) => ({ ...o, [it.id]: !o[it.id] }))} className="rounded border px-3 py-1.5 text-xs">{analysisOpen[it.id] ? 'Hide Analysis' : 'View Analysis'}</button>
                    </>
                  ) : (
                    <button onClick={() => sendToCorroboration(it)} className="rounded border px-3 py-1.5 text-xs">Send to Corroboration</button>
                  )}
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
              {corroMap[it.id] && analysisOpen[it.id] ? (
                <div className="mt-2 rounded border bg-white/50 p-2 text-xs dark:border-zinc-800 dark:bg-zinc-900/40">
                  <div className="mb-1 flex items-center justify-between">
                    <div className="font-medium">Corroboration Analysis</div>
                    <div className="font-mono text-[10px] text-zinc-500">Engine: v2</div>
                  </div>
                  {analysis[it.id]?.error ? (
                    <div className="text-red-600">{analysis[it.id]?.error}</div>
                  ) : analysis[it.id]?.loading ? (
                    <div className="text-zinc-500">Loading…</div>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <span className="rounded bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">Score: {(analysis[it.id]?.doc as any)?.score ?? 0}</span>
                        <span className="rounded bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">Summary: {(analysis[it.id]?.doc as any)?.summary ?? ''}</span>
                      </div>
                      <div>
                        <div className="mb-1 font-medium">Result</div>
                        <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded bg-zinc-50 p-2 dark:bg-zinc-950">{JSON.stringify(analysis[it.id]?.doc ?? {}, null, 2)}</pre>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
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
