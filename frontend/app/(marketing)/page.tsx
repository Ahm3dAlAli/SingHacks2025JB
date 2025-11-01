import Link from "next/link";
import type { ComponentType, SVGProps } from "react";
import {
  Scale,
  Brain,
  Bell,
  FileText,
  Settings,
  Activity,
  Users,
  Plug,
  RefreshCw,
  CheckCircle,
  BarChart3,
  ShieldCheck,
} from "lucide-react";
import HeroAuthAction from "@/components/HeroAuthAction";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-zinc-50 dark:from-black dark:to-zinc-900">
      {/* Hero */}
      <header className="mx-auto max-w-5xl px-6 pt-24 pb-16 text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-6xl">
          ⚖️ Smarter Compliance. Faster Decisions.
        </h1>
        <p className="mx-auto mt-5 max-w-3xl text-lg leading-7 text-zinc-600 dark:text-zinc-400">
          Meet the all-in-one Regulatory Intelligence & Alert Management Platform that helps financial institutions stay compliant,
          detect risk early, and close cases faster — powered by automation, auditability, and AI.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="#get-started"
            className="rounded-full bg-primary px-6 py-3 text-sm font-medium text-primary-foreground shadow hover:opacity-90"
          >
            Get Started
          </Link>
          <Link
            href="#features"
            className="rounded-full border border-zinc-200 px-6 py-3 text-sm font-medium text-zinc-900 hover:bg-zinc-100 dark:border-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-800"
          >
            Explore Features
          </Link>
          <HeroAuthAction />
        </div>
      </header>

      {/* Ingest, Understand, Act */}
      <section id="features" className="mx-auto max-w-5xl px-6 pb-12">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          🧠 Ingest, Understand, and Act — Automatically
        </h2>
        <p className="mt-2 max-w-3xl text-zinc-600 dark:text-zinc-400">
          Our platform connects regulatory sources, rule logic, transactions, and alerts into one seamless workflow.
        </p>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Bullet Icon={Scale} title="Regulatory Ingestion" text="Auto‑crawl updates from MAS, HKMA, FINMA, and more — no manual tracking." />
          <Bullet Icon={Settings} title="Rules Engine" text="Define, validate, and promote risk rules with version control and full traceability." />
          <Bullet Icon={Activity} title="Transaction Scoring" text="Stream or batch ingest data, evaluate instantly, and surface high‑risk entities in seconds." />
          <Bullet Icon={Brain} title="AI‑Powered Insights" text="Explain alerts, summarize risk, and recommend actions with agentic orchestration." />
        </div>
      </section>

      {/* Detection to Resolution */}
      <section className="mx-auto max-w-5xl px-6 pb-12">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          🔔 From Detection to Resolution — All in One Place
        </h2>
        <p className="mt-2 max-w-3xl text-zinc-600 dark:text-zinc-400">
          Everything your compliance and risk teams need, unified in a single dashboard.
        </p>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Bullet Icon={Bell} title="Alerts & Cases" text="Investigate alerts with full timelines, documents, and transactions in context." />
          <Bullet Icon={FileText} title="Documents & Evidence" text="Upload, OCR, and validate KYC/supporting docs — automatically scored for anomalies." />
          <Bullet Icon={CheckCircle} title="Remediation Actions" text="Trigger EDD, Re‑KYC, or escalation templates with one click." />
          <Bullet Icon={ShieldCheck} title="Reporting & Audit" text="Generate regulator‑ready PDFs and view lineage from transaction → rule → alert → report." />
        </div>
      </section>

      {/* Real-time & Traceable */}
      <section className="mx-auto max-w-5xl px-6 pb-12">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">📊 Real-Time, Transparent, and Traceable</h2>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Bullet Icon={Bell} title="Live updates" text="Real‑time updates for new or changing alerts." />
          <Bullet Icon={BarChart3} title="SLAs & trends" text="SLA dashboards, trend analytics, and performance metrics." />
          <Bullet Icon={FileText} title="Audit trails" text="End‑to‑end audit trails for every rule, document, and decision." />
        </div>
      </section>

      {/* Teams */}
      <section className="mx-auto max-w-5xl px-6 pb-12">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">👩‍💼 Built for Every Team</h2>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Role title="Front Office / RM" text="Instant visibility on client alerts and risk signals." />
          <Role title="Compliance" text="Deep investigation, remediation, and reporting in one view." />
          <Role title="Legal / Audit" text="Read‑only transparency with references and evidence trails." />
          <Role title="Admins" text="Full control over rules, jobs, integrations, and user roles." />
        </div>
      </section>

      {/* Integrations */}
      <section className="mx-auto max-w-5xl px-6 pb-12">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">🤝 Integrations That Fit Your Workflow</h2>
        <p className="mt-2 max-w-3xl text-zinc-600 dark:text-zinc-400">
          Connect seamlessly with Jira, Slack, ServiceNow, or internal case systems. Sync alerts, reports, and updates without leaving the platform.
        </p>
        <div className="mt-4 flex gap-3">
          <Bullet Icon={Plug} title="APIs & Webhooks" text="Integrate bi‑directionally with your stack." />
          <Bullet Icon={RefreshCw} title="Sync jobs" text="Schedule imports, replays, and exports." />
        </div>
      </section>

      {/* Always Up to Date */}
      <section className="mx-auto max-w-5xl px-6 pb-12">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">🔍 Always Up to Date</h2>
        <p className="mt-2 max-w-3xl text-zinc-600 dark:text-zinc-400">
          Automatic regulatory crawlers, scheduled replays, and AI tuning ensure your controls evolve with the latest rules and feedback.
        </p>
      </section>

      {/* Why Us */}
      <section className="mx-auto max-w-5xl px-6 pb-16">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">✅ Why Teams Choose Us</h2>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Bullet Icon={CheckCircle} title="Reduce alert fatigue" text="Cut noise by up to 60% with intelligent triage." />
          <Bullet Icon={Activity} title="Save review time" text="Over 50% faster through automation and guidance." />
          <Bullet Icon={FileText} title="Audit‑ready" text="Deliver complete, auditable reports in minutes." />
        </div>
      </section>

      {/* CTA */}
      <section id="get-started" className="mx-auto max-w-5xl px-6 pb-24 text-center">
        <div className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Ready to accelerate compliance?</h2>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400">
            Sign in to explore the mock demo and workflow.
          </p>
          <div className="mt-5 flex items-center justify-center gap-3">
            <Link
              href="/login"
              className="rounded-full bg-primary px-6 py-3 text-sm font-medium text-primary-foreground shadow hover:opacity-90"
            >
              Login to Demo
            </Link>
            <Link
              href="#features"
              className="rounded-full border border-zinc-200 px-6 py-3 text-sm font-medium text-zinc-900 hover:bg-zinc-100 dark:border-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-800"
            >
              Explore Features
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mx-auto max-w-5xl px-6 pb-12 text-center text-sm text-zinc-500">
        <p>© 2025 SingHacks. All rights reserved.</p>
      </footer>
    </div>
  );
}

type FeatureProps = {
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  title: string;
  text: string;
};

function Bullet({ Icon, title, text }: FeatureProps) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-5 w-5 text-zinc-900 dark:text-zinc-50" />
        <div>
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-400">{text}</p>
        </div>
      </div>
    </div>
  );
}

function Role({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{title}</h3>
      <p className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-400">{text}</p>
    </div>
  );
}
