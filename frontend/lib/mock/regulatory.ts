export type RegUpdate = {
  id: string;
  authority: "MAS" | "HKMA" | "FINMA" | "FCA" | "AUSTRAC";
  date: string; // ISO
  title: string;
  summary: string;
  url: string;
  tags: string[];
};

function seededNumber(str: string) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

const AUTH: RegUpdate["authority"][] = ["MAS", "HKMA", "FINMA", "FCA", "AUSTRAC"];
const TAGS = ["AML/CFT", "Sanctions", "KYC", "Reporting", "Market Conduct"];

export function listRegulatoryUpdates(params?: { authority?: string; q?: string }) : RegUpdate[] {
  const base = Array.from({ length: 18 }, (_, i) => generateUpdate(`reg-${i+1}`));
  let items = base;
  if (params?.authority) items = items.filter(u => u.authority.toLowerCase() === params!.authority!.toLowerCase());
  if (params?.q) {
    const t = params.q.toLowerCase();
    items = items.filter(u => u.title.toLowerCase().includes(t) || u.summary.toLowerCase().includes(t));
  }
  return items.sort((a,b)=> b.date.localeCompare(a.date));
}

export function generateUpdate(id: string): RegUpdate {
  const seed = seededNumber(id);
  const auth = AUTH[seed % AUTH.length];
  const d = new Date(Date.now() - (seed % 30) * 24 * 3600_000).toISOString();
  const topic = TAGS[seed % TAGS.length];
  const title = `${auth}: Guidance update on ${topic.toLowerCase()}`;
  const summary = `Regulatory notice on ${topic} with clarifications for institutions on scope, thresholds, and reporting timelines. This is demo text.`;
  const url = `https://example.org/${auth.toLowerCase()}/${id}`;
  const tags = [topic, seed % 2 ? "Clarification" : "Consultation"];
  return { id, authority: auth, date: d, title, summary, url, tags };
}

