"use client";

import Link from "next/link";
import { useAuth } from "@/lib/use-auth";

export default function HeroAuthAction() {
  const { loggedIn } = useAuth();

  if (loggedIn) {
    return (
      <Link
        href="/dashboard"
        className="rounded-full border border-zinc-200 px-6 py-3 text-sm font-medium text-zinc-900 hover:bg-zinc-100 dark:border-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-800"
      >
        Dashboard
      </Link>
    );
  }

  return (
    <Link
      href="/login"
      className="rounded-full border border-zinc-200 px-6 py-3 text-sm font-medium text-zinc-900 hover:bg-zinc-100 dark:border-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-800"
    >
      Login
    </Link>
  );
}
