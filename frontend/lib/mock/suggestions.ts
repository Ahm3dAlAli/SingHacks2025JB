export type RuleSuggestionStatus =
  | "needs_review"
  | "approved"
  | "rejected"
  | "promoted";

export type RuleSuggestion = {
  id: string;
  updateId: string;
  ruleId: string | null;
  title: string;
  rationale: string;
  confidence: number; // 0..1
  impact: { estimatedHits: number; note?: string } | null;
  suggestedDsl: string; // simplified DSL for demo
  currentDsl?: string | null;
  unifiedDiff: string; // human-friendly unified diff
  structuredDiff: { path: string; from?: string | number; to?: string | number; note?: string }[];
  status: RuleSuggestionStatus;
  createdAt: string;
  comments: { id: string; author: string; text: string; at: string }[];
  // lifecycle artifacts
  createdVersionId?: string; // when approved
  compileArtifact?: string; // when compiled for promotion
  promotedAt?: string; // when promoted
};

import { generateUpdate, RegUpdate } from "@/lib/mock/regulatory";
import { compileRuleset, getRule, listRules, promoteArtifact } from "@/lib/mock/rules";

// In-memory store (module-level). Suitable for demo only.
const SUGGESTIONS = new Map<string, RuleSuggestion>();

function uid(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 8)}-${Date.now().toString(36)}`;
}

export function listSuggestions(params?: { status?: RuleSuggestionStatus }) {
  const items = Array.from(SUGGESTIONS.values());
  if (!params?.status) return items.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  return items
    .filter((s) => s.status === params.status)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function getSuggestion(id: string) {
  return SUGGESTIONS.get(id) || null;
}

export function addComment(id: string, author: string, text: string) {
  const s = SUGGESTIONS.get(id);
  if (!s) return null;
  s.comments.push({ id: uid("c"), author, text, at: new Date().toISOString() });
  return s;
}

// Deterministic mock: choose a rule based on update id hash
function pickRuleForUpdate(updateId: string) {
  const rules = listRules();
  const idx = Math.abs(hash(updateId)) % rules.length;
  return rules[idx];
}

function hash(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return h;
}

function makeUnifiedDiff(before: string, after: string) {
  return [
    "--- current",
    "+++ suggested",
    "@@",
    `-${before}`,
    `+${after}`,
  ].join("\n");
}

export function createSuggestionFromUpdate(updateId: string) {
  // Reuse an existing pending suggestion for the same update to avoid duplicates
  for (const s of SUGGESTIONS.values()) {
    if (s.updateId === updateId && s.status === "needs_review") {
      return s;
    }
  }
  // Pull update metadata (mock)
  const update: RegUpdate = generateUpdate(updateId);
  // Pick a rule and produce a threshold change for demo
  const rule = pickRuleForUpdate(updateId);
  const beforeDsl = getRule(rule.id).history[0].dsl;

  // Heuristic: if update mentions threshold, lower to 3000, else add a geo filter
  const isThreshold = /threshold|amount|limit|cash|transaction/i.test(update.summary + " " + update.title);
  const afterDsl = isThreshold
    ? beforeDsl.replace(/(\d{3,5})/g, (m) => (parseInt(m, 10) > 3000 ? "3000" : m)) + " // apply new $3k threshold"
    : beforeDsl + " AND geo in {HK,SG}";

  const suggestion: RuleSuggestion = {
    id: uid("sug"),
    updateId,
    ruleId: rule.id,
    title: `Update ${rule.name} per ${update.authority}`,
    rationale: `Map ${update.authority} update to ${rule.name}. Adjust parameters to align with guidance.`,
    confidence: 0.78,
    impact: { estimatedHits: 127, note: "Based on last 24h replay (mock)" },
    suggestedDsl: afterDsl,
    currentDsl: beforeDsl,
    unifiedDiff: makeUnifiedDiff(beforeDsl, afterDsl),
    structuredDiff: isThreshold
      ? [{ path: "threshold", from: 10000, to: 3000, note: "Lowered per guidance" }]
      : [{ path: "geo", from: "any", to: "{HK,SG}", note: "Add risk region focus" }],
    status: "needs_review",
    createdAt: new Date().toISOString(),
    comments: [],
  };
  SUGGESTIONS.set(suggestion.id, suggestion);
  return suggestion;
}

export function listByUpdate(updateId: string) {
  return Array.from(SUGGESTIONS.values()).filter((s) => s.updateId === updateId);
}

export function approveSuggestion(id: string) {
  const s = SUGGESTIONS.get(id);
  if (!s) return null;
  s.status = "approved";
  // create a mock new version id for history/diff linking
  s.createdVersionId = `v-${s.ruleId ?? "new"}-${Math.abs(hash(id)) % 100}`;
  return s;
}

export function rejectSuggestion(id: string) {
  const s = SUGGESTIONS.get(id);
  if (!s) return null;
  s.status = "rejected";
  return s;
}

export function promoteSuggestion(id: string) {
  const s = SUGGESTIONS.get(id);
  if (!s) return null;
  // compile and promote using rules mocks
  const comp = compileRuleset({ rules: [s.suggestedDsl] as any });
  s.compileArtifact = comp.artifact;
  const prom = promoteArtifact({ artifact: comp.artifact });
  s.promotedAt = prom.activatedAt;
  s.status = "promoted";
  return s;
}

export function validateSuggestion(id: string) {
  const s = SUGGESTIONS.get(id);
  if (!s) return { ok: false, warnings: ["Not found"] };
  // simple heuristic: warn if uses select *
  const warnings = s.suggestedDsl.includes("select *") ? ["Avoid broad selections"] : [];
  return { ok: true, warnings };
}

export function replaySuggestion(id: string) {
  const s = SUGGESTIONS.get(id);
  if (!s) return { ok: false };
  const hours = 24;
  const evaluated = 2000 + (Math.abs(hash(id)) % 5000);
  const regressions = Math.floor(evaluated * 0.03);
  const improvements = Math.floor(evaluated * 0.05);
  return { ok: true, hours, evaluated, regressions, improvements };
}
