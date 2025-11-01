"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn, logout } from "@/lib/auth";

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  function onLogout() {
    logout();
    router.push("/");
  }

  return (
    <div>
      <h1 className="text-3xl font-semibold text-zinc-900 dark:text-zinc-50">Dashboard</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        You are logged in with a mock token stored in localStorage.
      </p>
      <div className="mt-6 flex gap-3">
        <button
          onClick={onLogout}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Logout
        </button>
      </div>
    </div>
  );
}

