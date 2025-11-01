#!/usr/bin/env node
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const outDir = join(process.cwd(), "public", "guides", "suggestions-demo");
if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

const files = [
  { name: "01-login.svg", title: "Login" },
  { name: "02-reg-updates.svg", title: "Regulatory Updates" },
  { name: "03-new-applied.svg", title: "What’s New / Recently Applied" },
  { name: "04-suggestion-review.svg", title: "Suggestion Review" },
  { name: "05-card-states.svg", title: "Card States" },
];

function svgFor(title) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" viewBox="0 0 1200 700">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#eef2ff"/>
      <stop offset="100%" stop-color="#e0f2fe"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <rect x="40" y="40" width="1120" height="620" rx="16" fill="#ffffff" stroke="#d4d4d8"/>
  <text x="600" y="220" text-anchor="middle" font-family="ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto" font-size="42" fill="#0f172a">${title}</text>
  <text x="600" y="280" text-anchor="middle" font-family="ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto" font-size="18" fill="#475569">Placeholder screenshot — replace with real image</text>
  <g transform="translate(200,360)">
    <rect width="800" height="200" rx="12" fill="#f8fafc" stroke="#e5e7eb"/>
    <text x="400" y="110" text-anchor="middle" font-family="ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto" font-size="16" fill="#64748b">Demo UI box</text>
  </g>
</svg>`;
}

for (const f of files) {
  const p = join(outDir, f.name);
  writeFileSync(p, svgFor(f.title), "utf8");
  console.log("wrote", p);
}
