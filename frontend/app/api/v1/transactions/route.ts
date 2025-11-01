import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { parseTransactionsFullFromText } from "@/lib/parseTransactions";

const CANDIDATE_PATHS = [
  path.join(process.cwd(), "public", "data", "transactions_mock_1000_for_participants.csv"),
  path.join(process.cwd(), "public", "data", "transactions.csv"),
];

export async function GET() {
  let text: string | null = null;
  for (const p of CANDIDATE_PATHS) {
    try {
      text = await fs.readFile(p, "utf8");
      break;
    } catch {}
  }
  if (!text) return NextResponse.json({ items: [], errors: [{ row: 0, message: "No CSV found" }], warnings: [] });
  const { rows, errors, warnings } = parseTransactionsFullFromText(text);
  return NextResponse.json({ items: rows, errors, warnings });
}

