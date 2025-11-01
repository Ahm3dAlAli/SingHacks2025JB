"use client";

import Link from "next/link";
import { useCallback } from "react";
import { logout } from "@/lib/auth";
import { useAuth } from "@/lib/use-auth";
import { useRouter } from "next/navigation";

export default function Header() {
  const router = useRouter();
  const { loggedIn } = useAuth();

  const onLogout = useCallback(() => {
    logout();
    setLoggedIn(false);
    router.push("/");
  }, [router]);

  return (
    <nav className="sticky top-0 z-10 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <Link href="/" className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
          SingHacks
        </Link>
        <div className="flex items-center gap-2">
          {!loggedIn ? (
            <Link
              href="/login"
              className="rounded-full border border-primary px-4 py-1.5 text-sm font-medium text-primary hover:bg-primary/10"
            >
              Login
            </Link>
          ) : (
            <>
              <Link
                href="/dashboard"
                className="rounded-full border border-primary px-4 py-1.5 text-sm font-medium text-primary hover:bg-primary/10"
              >
                Dashboard
              </Link>
              <button
                onClick={onLogout}
                className="rounded-full bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
              >
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
