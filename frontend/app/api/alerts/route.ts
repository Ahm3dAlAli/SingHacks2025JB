import { NextResponse } from "next/server";
import { loadTransactions, computeSeverity } from "@/lib/server/txData";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const severityFilter = url.searchParams.get("severity");
  const statusFilter = url.searchParams.get("status");
  const entityLike = url.searchParams.get("entity");
  const page = Math.max(1, parseInt(url.searchParams.get("page") || "1", 10));
  const pageSize = Math.max(1, Math.min(200, parseInt(url.searchParams.get("pageSize") || "24", 10)));
  const { rows } = await loadTransactions();
  const items = rows.map((tx) => ({
    id: tx.transaction_id,
    entity: tx.display_counterparty || tx.beneficiary_name || tx.originator_name,
    severity: computeSeverity(tx),
    status: ("new" as const),
    createdAt: tx.booking_datetime,
    amount: Math.abs(tx.amount),
    currency: tx.currency,
    direction: tx.display_direction ?? (tx.amount >= 0 ? "IN" : "OUT"),
    originator_name: tx.originator_name,
    originator_account_last4: tx.originator_account ? tx.originator_account.slice(-4) : undefined,
    beneficiary_name: tx.beneficiary_name,
    beneficiary_account_last4: tx.beneficiary_account ? tx.beneficiary_account.slice(-4) : undefined,
    sanctions_screening: tx.sanctions_screening ?? undefined,
    channel: tx.channel,
    product_type: tx.product_type,
    booking_jurisdiction: tx.booking_jurisdiction,
    regulator: tx.regulator,
  }));
  const filtered = items.filter((a) => {
    if (severityFilter && a.severity !== severityFilter) return false;
    if (statusFilter && a.status !== statusFilter) return false;
    if (entityLike) {
      const s = entityLike.toLowerCase();
      if (!a.entity?.toLowerCase().includes(s)) return false;
    }
    return true;
  });
  // Sort by createdAt desc then id
  filtered.sort((a, b) => (new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()) || a.id.localeCompare(b.id));
  const total = filtered.length;
  const start = (page - 1) * pageSize;
  const paged = filtered.slice(start, start + pageSize);
  return NextResponse.json({ items: paged, total, page, pageSize });
}

export async function POST(request: Request) {
  // Not supported in CSV-driven demo; return 405
  return NextResponse.json({ error: "Creating alerts is disabled in CSV demo" }, { status: 405 });
}
