# Repository Guidelines

## Project Structure & Module Organization
- `app/`: App Router pages, layouts, global styles (`globals.css`). Edit `app/page.tsx` to change the homepage.
- `lib/`: Shared utilities (e.g., `lib/utils.ts`).
- `public/`: Static assets served from `/` (SVGs, images).
- Config: `next.config.ts`, `tsconfig.json` (path alias `@/*`), `eslint.config.mjs`, `postcss.config.mjs`.

## Build, Test, and Development Commands
- Develop: `pnpm dev` — runs Next.js locally at `http://localhost:3000`.
- Build: `pnpm build` — compiles the production build.
- Start: `pnpm start` — serves the production build.
- Lint: `pnpm lint` — runs ESLint with Next.js rules.

Tip: This repo uses `pnpm` (see `pnpm-lock.yaml`). Prefer `pnpm` over npm/yarn for consistency.

## Coding Style & Naming Conventions
- Language: TypeScript (strict mode). React Server Components by default (App Router).
- Linting: ESLint with `eslint-config-next` (core web vitals + TypeScript). Fix issues before committing.
- Styling: Tailwind CSS v4 via PostCSS. Global tokens live in `app/globals.css`.
- Imports: use alias `@/*` from `tsconfig.json` (e.g., `import { cn } from "@/lib/utils"`).
- Naming: React components in PascalCase, route files in lowercase (`page.tsx`, `layout.tsx`). Keep files/folders kebab-case under `app/` segments.

## Testing Guidelines
- No test runner is configured yet. If adding tests:
  - Unit: Vitest or Jest + React Testing Library, colocate as `*.test.ts(x)` next to source.
  - E2E: Playwright under `e2e/` with `*.spec.ts`.
  - Add a `test` script (e.g., `"test": "vitest"`) and ensure CI runs `pnpm lint && pnpm test`.

## Commit & Pull Request Guidelines
- Commits: clear, imperative subjects (e.g., "feat: add homepage hero"). Group related changes; keep scope focused.
- PRs: include a concise description, linked issue(s), screenshots or clips for UI changes, and notes on testing/impact.
- Quality gate: PRs should pass `pnpm lint` and build successfully. Include checklist items if adding tests/config.

## Security & Configuration Tips
- Secrets: never commit `.env*`. Use `.env.local` for development; prefix public vars with `NEXT_PUBLIC_`.
- Dependencies: favor minor/patch bumps; verify Next.js compatibility before major upgrades.
