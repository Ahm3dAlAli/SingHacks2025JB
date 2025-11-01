import { NextResponse } from "next/server";
import { loadTransactions } from "@/lib/server/txData";
import { mockAdverseMediaForName } from "@/lib/server/adverseMedia";

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

export async function POST(_: Request, ctx: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await ctx.params;
  const { rows } = await loadTransactions();

  // Resolve entity name from id
  let name: string | null = null;
  for (const tx of rows) {
    if (tx.originator_name && `n-${slugify(tx.originator_name)}` === entityId) { name = tx.originator_name; break; }
    if (tx.beneficiary_name && `n-${slugify(tx.beneficiary_name)}` === entityId) { name = tx.beneficiary_name; break; }
  }
  if (!name) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const related = rows.filter((tx) => tx.originator_name === name || tx.beneficiary_name === name);
  if (related.length === 0) return NextResponse.json({ entityId, name, totals: { inflow: 0, outflow: 0, net: 0 }, counts: { txns: 0, counterparties: 0, currencies: 0, daysActive: 0 }, lastSeen: null, topCounterparties: [], currencies: [], channels: [], sanctions: { clear: 0, potential: 0, hit: 0, unknown: 0 }, flags: [], summary: "No transactions found for this client." });

  let inflow = 0, outflow = 0;
  const cpty = new Map<string, { name: string; count: number; amount: number }>();
  const ccy = new Map<string, number>();
  const ch = new Map<string, number>();
  const sanc = { clear: 0, potential: 0, hit: 0, unknown: 0 };
  let minTs = Number.POSITIVE_INFINITY;
  let maxTs = 0;
  let pepCount = 0;
  let kycOverdue = 0;
  const amlScores: number[] = [];
  const purposes = new Map<string, number>();
  const purposeTexts: string[] = [];

  for (const tx of related) {
    const amtAbs = Math.abs(tx.amount);
    if (tx.beneficiary_name === name) inflow += amtAbs;
    if (tx.originator_name === name) outflow += amtAbs;
    const other = tx.beneficiary_name === name ? (tx.originator_name || "(unknown)") : (tx.beneficiary_name || "(unknown)");
    const e = cpty.get(other) || { name: other, count: 0, amount: 0 };
    e.count += 1; e.amount += amtAbs; cpty.set(other, e);
    ccy.set(tx.currency, (ccy.get(tx.currency) || 0) + amtAbs);
    ch.set(tx.channel, (ch.get(tx.channel) || 0) + 1);
    const s = (tx.sanctions_screening ?? "").toString().toUpperCase();
    if (s === "HIT") sanc.hit++; else if (s === "POTENTIAL_MATCH") sanc.potential++; else if (s === "CLEAR") sanc.clear++; else sanc.unknown++;
    const t = new Date(tx.booking_datetime).getTime();
    if (!isNaN(t)) { minTs = Math.min(minTs, t); maxTs = Math.max(maxTs, t); }
    if (tx.customer_is_pep || tx.pep_flag) pepCount++;
    if (typeof tx.aml_risk_score === 'number') amlScores.push(tx.aml_risk_score);
    if (tx.kyc_due_date) {
      const due = new Date(tx.kyc_due_date + "T00:00:00+08:00").getTime();
      if (!isNaN(due) && due < Date.now()) kycOverdue++;
    }
    const p = (tx.swift_f70_purpose || tx.purpose_code || '').toString().trim();
    if (p) purposes.set(p, (purposes.get(p) || 0) + 1);
    const n = (tx.narrative || '').toString().trim();
    if (n) purposeTexts.push(n);
  }

  const net = inflow - outflow;
  const counterparties = Array.from(cpty.values()).sort((a, b) => b.amount - a.amount).slice(0, 10);
  const currencies = Array.from(ccy.entries()).map(([code, amount]) => ({ code, amount })).sort((a, b) => b.amount - a.amount).slice(0, 10);
  const channels = Array.from(ch.entries()).map(([channel, count]) => ({ channel, count })).sort((a, b) => b.count - a.count).slice(0, 10);
  const daysActive = (isFinite(minTs) && maxTs) ? Math.max(1, Math.round((maxTs - minTs) / 86400000) + 1) : 0;
  const lastSeen = maxTs ? new Date(maxTs).toISOString() : null;
  const flags: string[] = [];
  if (pepCount > 0) flags.push(`PEP flags in ${pepCount} txn(s)`);
  if (kycOverdue > 0) flags.push(`KYC overdue in ${kycOverdue} txn(s)`);

  const summary = `${name} has ${related.length} transactions across ${currencies.length} currencies and ${counterparties.length} counterparties. Inflow ${inflow.toLocaleString()} / Outflow ${outflow.toLocaleString()} (net ${net.toLocaleString()}).`;

  // KYC profile (derived, MVP)
  const corporateHints = ["PTE", "LTD", "INC", "LLC", "PLC", "CORP", "CO ", "CO.", "COMPANY"];
  const isPrivateIndividual = !corporateHints.some((h) => (name || "").toUpperCase().includes(h));
  const adv = mockAdverseMediaForName(name);
  const adverseMedia = adv.count > 0;
  const adverseInfo = adverseMedia; // MVP: same as media flag
  const maxAml = amlScores.length ? Math.max(...amlScores) : 0;
  // Derive a clearer reputational risk with multiple signals
  const totalVolume = inflow + outflow;
  const recent = maxTs ? (Date.now() - maxTs) <= 7 * 86400000 : false; // last 7 days
  let reputationalRisk: "low" | "medium" | "high" = "low";
  if (sanc.hit > 0 || pepCount > 0 || maxAml >= 90) {
    reputationalRisk = "high";
  } else if (sanc.potential > 0 || kycOverdue > 0 || maxAml >= 70 || totalVolume > 1_000_000 || (recent && related.length >= 20)) {
    reputationalRisk = "medium";
  }
  const reputationalReasons: string[] = [];
  if (sanc.hit > 0) reputationalReasons.push("Sanctions hit present");
  if (sanc.potential > 0) reputationalReasons.push("Sanctions potential match");
  if (pepCount > 0) reputationalReasons.push("PEP involvement in transactions");
  if (kycOverdue > 0) reputationalReasons.push("KYC overdue");
  if (adv.count > 0) reputationalReasons.push(`Adverse media mentions (${adv.count})`);
  if (maxAml >= 90) reputationalReasons.push("High AML risk score (≥90)");
  else if (maxAml >= 70) reputationalReasons.push("Elevated AML risk score (≥70)");
  if (totalVolume > 1_000_000) reputationalReasons.push("High total volume (> 1,000,000)");
  if (recent && related.length >= 20) reputationalReasons.push("High recent activity (20+ tx in last 7 days)");
  const reasonPurpose = (() => {
    if (purposes.size > 0) return Array.from(purposes.entries()).sort((a, b) => b[1] - a[1])[0][0];
    if (purposeTexts.length > 0) return purposeTexts[0].slice(0, 120);
    return null;
  })();
  const businessActivities = Array.from(ch.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([channel]) => channel);
  const assetBreakdown = currencies.map((c) => ({ label: c.code, amount: c.amount }));
  const sowDocumentedCount = related.reduce((acc, tx) => acc + (tx.sow_documented ? 1 : 0), 0);
  const sourceOfWealth = sowDocumentedCount > 0 ? "Documented" : "Not documented";
  const sourceOfIncome = null; // Unknown in MVP

  return NextResponse.json({
    entityId,
    name,
    summary,
    totals: { inflow, outflow, net },
    counts: { txns: related.length, counterparties: counterparties.length, currencies: currencies.length, daysActive },
    lastSeen,
    topCounterparties: counterparties,
    currencies,
    channels,
    sanctions: sanc,
    flags,
    adverseMedia: adv,
    kyc: {
      type: isPrivateIndividual ? "Private Individual" : "Corporate",
      pep: pepCount > 0,
      adverseInformation: adverseInfo,
      adverseMedia,
      reputationalRisk,
      insiderFlag: false,
      reasonPurpose,
      education: null,
      familyBackground: null,
      currentOccupation: null,
      businessActivities,
      sourceOfWealth,
      assetBreakdown,
      sourceOfIncome,
    },
    reputationalReasons,
  });
}
