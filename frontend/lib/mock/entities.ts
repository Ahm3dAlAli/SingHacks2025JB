export type Person = {
  id: string;
  name: string;
  nationality: string;
  dob: string;
  occupation: string;
  employer: string;
  relatives: { relation: string; name: string }[];
};

function seededNumber(str: string) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

const names = ["Alex Lee", "Jamie Tan", "Priya Singh", "Wei Chen", "Maria Gomez", "Samir Patel", "Aiko Sato", "Liam O'Connor"];
const jobs = ["Portfolio Manager", "Entrepreneur", "CTO", "Consultant", "Trader", "Lawyer", "Doctor", "Architect"];
const employers = ["Vertex Capital", "Nova Labs", "Independent", "Orion Partners", "Blue Harbor", "City Hospital", "Universal Bank", "Civic Group"];
const nationalities = ["SG", "HK", "CH", "IN", "US", "GB", "JP", "DE"];

export function listPeople(): Person[] {
  return Array.from({ length: 8 }, (_, i) => generatePerson(`p-${i + 1}`));
}

export function generatePerson(id: string): Person {
  const seed = seededNumber(id);
  const idx = seed % names.length;
  const jdx = seed % jobs.length;
  const edx = seed % employers.length;
  const ndx = seed % nationalities.length;
  const year = 1965 + (seed % 40);
  const month = (seed % 12) + 1;
  const day = (seed % 28) + 1;
  return {
    id,
    name: names[idx],
    nationality: nationalities[ndx],
    dob: `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
    occupation: jobs[jdx],
    employer: employers[edx],
    relatives: [
      { relation: "spouse", name: names[(idx + 3) % names.length] },
      { relation: "sibling", name: names[(idx + 5) % names.length] },
    ],
  };
}

export type BackgroundReport = {
  entityId: string;
  summary: string;
  estNetWorthUSD: number;
  reasoning: {
    assets: string[];
    workLife: string[];
    family: string[];
    social: string[];
  };
  sources: { label: string; url: string }[];
};

export function generateBackgroundReport(entityId: string): BackgroundReport {
  const person = generatePerson(entityId);
  const seed = seededNumber(entityId);
  const est = 500_000 + (seed % 5) * 750_000 + (person.employer.includes("Capital") ? 800_000 : 0);
  return {
    entityId,
    summary: `${person.name} (${person.occupation}, ${person.employer}) shows moderate to high wealth indicators with diversified assets and a stable professional history. No direct adverse media detected in the last 24 months.`,
    estNetWorthUSD: est,
    reasoning: {
      assets: [
        "Condo ownership inferred from property listings in core districts",
        "Equity holdings via company registry filings",
        "Possible private investments (angel/seed) from press coverage",
      ],
      workLife: [
        `Tenure at ${person.employer} as ${person.occupation}`,
        "Prior roles suggest increasing seniority and compensation",
      ],
      family: person.relatives.map((r) => `Relative: ${r.relation} — ${r.name}`),
      social: ["Professional network indicates exposure to finance/tech circles", "No sanctioned entities found in proximity (mock)"]
    },
    sources: [
      { label: "News search", url: "https://news.google.com/" },
      { label: "Company registry", url: "https://opencorporates.com/" },
      { label: "Professional profile", url: "https://www.linkedin.com/" },
      { label: "Property listings", url: "https://www.propertyguru.com.sg/" },
    ],
  };
}

