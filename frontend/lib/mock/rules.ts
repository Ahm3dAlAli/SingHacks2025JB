export type Rule = {
  id: string;
  name: string;
  status: "active" | "inactive";
  versionId: string;
  dsl: string;
  createdAt: string;
};

export type RuleVersion = {
  versionId: string;
  ruleId: string;
  dsl: string;
  createdAt: string;
};

function seededNumber(str: string) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

export function listRules(): Rule[] {
  return [1, 2, 3].map((i) => {
    const id = `rule-${i}`;
    const versionId = `v-${i}-0`;
    return {
      id,
      name: i === 1 ? "High Amount" : i === 2 ? "Velocity Anomaly" : "Geo Risk",
      status: i === 3 ? "inactive" : "active",
      versionId,
      dsl: `rule ${id} when ... then score ...`,
      createdAt: new Date(Date.now() - i * 24 * 3600_000).toISOString(),
    };
  });
}

export function getRule(ruleId: string): { rule: Rule; history: RuleVersion[] } {
  const base = listRules().find((r) => r.id === ruleId) ?? listRules()[0];
  const history: RuleVersion[] = [0, 1, 2].map((j) => ({
    versionId: `v-${ruleId}-${j}`,
    ruleId,
    dsl: `${base.dsl} // version ${j}`,
    createdAt: new Date(Date.now() - (j + 1) * 12 * 3600_000).toISOString(),
  }));
  return { rule: base, history };
}

export function validateRule(payload: { dsl?: string; json?: unknown }) {
  const ok = !!(payload.dsl || payload.json);
  const warnings = payload.dsl?.includes("select *") ? ["Avoid broad selections"] : [];
  return { ok, warnings };
}

export function compileRuleset(payload: { rules: string[] | undefined }) {
  const input = (payload.rules ?? []).join(",");
  const hash = `art-${seededNumber(input + Date.now())}`;
  return { artifact: hash, count: payload.rules?.length ?? 0 };
}

export function promoteArtifact(payload: { artifact: string }) {
  return { ok: true, artifact: payload.artifact, activatedAt: new Date().toISOString() };
}

export function versionDiff(versionId: string) {
  return { versionId, summary: "Changed threshold from 50k to 40k; added geo filter" };
}

export function replay(payload: { hours: number }) {
  const hours = payload.hours ?? 1;
  return { ok: true, hours, evaluated: hours * 1000, regressions: Math.floor(hours * 0.2) };
}

