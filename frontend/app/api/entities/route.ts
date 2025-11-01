import { NextResponse } from "next/server";
import { loadTransactions } from "@/lib/server/txData";

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

export async function GET() {
  const { rows } = await loadTransactions();
  type Person = { id: string; name: string; nationality: string; dob: string; occupation: string; employer: string };
  const map = new Map<string, Person & { _countries: Record<string, number> }>();
  const bump = (id: string, name: string, country: string) => {
    const p = map.get(id) || { id, name, nationality: "", dob: "", occupation: "", employer: "", _countries: {} };
    p._countries[country] = (p._countries[country] || 0) + 1;
    map.set(id, p);
  };
  for (const tx of rows) {
    if (tx.originator_name) bump(`n-${slugify(tx.originator_name)}`, tx.originator_name, tx.originator_country || "");
    if (tx.beneficiary_name) bump(`n-${slugify(tx.beneficiary_name)}`, tx.beneficiary_name, tx.beneficiary_country || "");
  }
  const items: Person[] = Array.from(map.values()).map((p) => {
    const topCountry = Object.entries(p._countries).sort((a, b) => b[1] - a[1])[0]?.[0] || "";
    return { id: p.id, name: p.name, nationality: topCountry || "—", dob: "", occupation: "", employer: "" };
  });
  // Basic sort by name
  items.sort((a, b) => a.name.localeCompare(b.name));
  return NextResponse.json({ items });
}
