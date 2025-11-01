export type Severity = "low" | "medium" | "high" | "critical";
export type Status = "new" | "acknowledged" | "in_progress" | "closed";

export type AlertListItem = {
  id: string;
  entity: string;
  severity: Severity;
  status: Status;
  createdAt: string;
};

export type AlertDetail = AlertListItem & {
  entityId: string;
  risk: number; // 0-100
  ruleHits: { id: string; name: string; score: number }[];
  transactions: { id: string; amount: number; currency: string; counterparty: string; ts: string }[];
  documents: { id: string; name: string; type: string; anomaly?: string }[];
};

export type TimelineEvent = {
  id: string;
  ts: string;
  type: "created" | "ack" | "status" | "comment";
  text: string;
};

const severities: Severity[] = ["low", "medium", "high", "critical"];
const statuses: Status[] = ["new", "acknowledged", "in_progress", "closed"];

function seededNumber(str: string) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

export function generateAlertDetail(alertId: string): AlertDetail {
  const seed = seededNumber(alertId);
  const entityId = `p-${(seed % 8) + 1}`;
  const entity = `Entity-${(seed % 7) + 1}`;
  const severity = severities[seed % severities.length];
  const status = statuses[seed % statuses.length];
  const createdAt = new Date(Date.now() - ((seed % 48) + 1) * 3600_000).toISOString();
  const risk = 50 + (seed % 50);
  return {
    id: alertId,
    entity,
    entityId,
    severity,
    status,
    createdAt,
    risk,
    ruleHits: [
      { id: "r1", name: "High-risk jurisdiction", score: 35 },
      { id: "r2", name: "Velocity anomaly", score: 20 },
    ],
    transactions: [
      { id: `${alertId}-t1`, amount: 12499.5, currency: "USD", counterparty: "ACME Ltd.", ts: new Date(Date.now() - 36e5).toISOString() },
      { id: `${alertId}-t2`, amount: 3200, currency: "USD", counterparty: "Foo Bar Co.", ts: new Date(Date.now() - 72e5).toISOString() },
    ],
    documents: [
      { id: `${alertId}-d1`, name: "Passport.pdf", type: "KYC", anomaly: "MRZ mismatch" },
      { id: `${alertId}-d2`, name: "UtilityBill.png", type: "Proof of Address" },
    ],
  };
}

export function generateTimeline(alertId: string): TimelineEvent[] {
  const now = Date.now();
  return [
    { id: `${alertId}-e1`, ts: new Date(now - 6 * 3600_000).toISOString(), type: "created", text: `Alert ${alertId} created` },
    { id: `${alertId}-e2`, ts: new Date(now - 5 * 3600_000).toISOString(), type: "status", text: "Status set to new" },
  ];
}

export function listAlerts(query?: { severity?: Severity; status?: Status; entity?: string }): AlertListItem[] {
  const baseIds = Array.from({ length: 8 }, (_, i) => `demo-${i + 1}`);
  let items = baseIds.map((id) => {
    const d = generateAlertDetail(id);
    const { ruleHits, transactions, documents, risk, ...rest } = d;
    return rest;
  });
  if (query?.severity) items = items.filter((a) => a.severity === query.severity);
  if (query?.status) items = items.filter((a) => a.status === query.status);
  if (query?.entity) items = items.filter((a) => a.entity === query.entity);
  return items;
}
