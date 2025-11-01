"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useRole } from "@/lib/use-role";
import { Permissions } from "@/lib/rbac";
import { isLoggedIn } from "@/lib/auth";

export default function DocDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  useEffect(() => { if (!isLoggedIn()) router.replace("/login"); }, [router]);
  const { role } = useRole();
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setError(null);
        setContent(null);
        const res = await fetch(`/api/docs/${slug}`);
        if (!res.ok) throw new Error("Failed to load doc");
        const data = (await res.json()) as { content: string };
        setContent(data.content);
      } catch (e: any) {
        setError(e.message || "Error");
      }
    })();
  }, [slug]);

  if (!Permissions.reviewDocs(role)) {
    return <div className="rounded border p-4 text-sm text-zinc-700 dark:text-zinc-300">Insufficient permissions to review documentation.</div>;
  }

  return (
    <div>
      <div className="mb-4">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Documentation</h1>
      </div>
      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/40">{error}</div>
      ) : content === null ? (
        <div className="h-48 animate-pulse rounded border bg-zinc-100 dark:bg-zinc-900" />
      ) : (
        <article className="prose max-w-none dark:prose-invert">
          <pre className="whitespace-pre-wrap text-sm">{content}</pre>
        </article>
      )}
    </div>
  );
}

