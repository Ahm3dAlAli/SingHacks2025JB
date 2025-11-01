export type Source = {
  id: string;
  name: string;
  type: "rss" | "web" | "email" | "webhook";
  url: string;
  lastScan: string | null;
  status: "idle" | "scanning" | "ok" | "error";
};

export type Item = {
  id: string;
  sourceId: string;
  title: string;
  url: string;
  mime: "application/pdf" | "text/html" | "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  status: "new" | "fetched" | "parsed" | "error";
  publishedAt: string;
};

export type Parse = {
  id: string;
  itemId: string;
  status: "queued" | "processing" | "done" | "error";
  sections?: { heading: string; text: string }[];
  extracted?: { key: string; value: string }[];
};

function seededNumber(str: string) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

const sourceList: Source[] = [
  { id: "mas", name: "Monetary Authority of Singapore", type: "rss", url: "https://www.mas.gov.sg/rss", lastScan: null, status: "idle" },
  { id: "hkma", name: "Hong Kong Monetary Authority", type: "web", url: "https://www.hkma.gov.hk/", lastScan: null, status: "idle" },
  { id: "finma", name: "Swiss FINMA", type: "rss", url: "https://www.finma.ch/en/news/rss/", lastScan: null, status: "idle" },
];

export function listSources(): Source[] {
  return sourceList.map((s) => ({ ...s, lastScan: s.lastScan ?? new Date(Date.now() - seededNumber(s.id) % 86_400_000).toISOString(), status: "ok" }));
}

export function listItems(): Item[] {
  const items: Item[] = [];
  for (const src of sourceList) {
    for (let i = 0; i < 5; i++) {
      const id = `${src.id}-item-${i + 1}`;
      const seed = seededNumber(id);
      const mime = seed % 3 === 0 ? "application/pdf" : seed % 3 === 1 ? "text/html" : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
      items.push({
        id,
        sourceId: src.id,
        title: `${src.id.toUpperCase()} notice ${(i + 1)}`,
        url: `https://example.org/${src.id}/${i + 1}`,
        mime,
        status: seed % 4 === 0 ? "parsed" : seed % 3 === 0 ? "fetched" : "new",
        publishedAt: new Date(Date.now() - (seed % (14 * 24 * 3600_000))).toISOString(),
      });
    }
  }
  return items.sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
}

export function getItem(itemId: string): Item | null {
  return listItems().find((i) => i.id === itemId) ?? null;
}

export function createParse(itemId: string): Parse {
  const id = `parse-${seededNumber(itemId + Date.now())}`;
  // For mock, immediately return "done" with sections
  const item = getItem(itemId)!;
  return {
    id,
    itemId,
    status: "done",
    sections: [
      { heading: "Scope", text: `Update concerning ${item.sourceId.toUpperCase()} supervisory expectations.` },
      { heading: "Requirements", text: "Reporting timelines, customer due diligence, and sanctions screening clarifications." },
    ],
    extracted: [
      { key: "authority", value: item.sourceId.toUpperCase() },
      { key: "publishedAt", value: item.publishedAt },
    ],
  };
}

export function getParse(parseId: string): Parse | null {
  // Deterministic mock: return a fabricated parse based on id
  if (!parseId.startsWith("parse-")) return null;
  const seed = seededNumber(parseId);
  const itemId = `mas-item-${(seed % 5) + 1}`;
  return {
    id: parseId,
    itemId,
    status: "done",
    sections: [
      { heading: "Summary", text: "This is a structured parse of the regulatory document." },
      { heading: "Obligations", text: "Maintain AML/CFT controls and reporting obligations." },
    ],
  };
}

