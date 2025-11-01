"use client";

import { useSyncExternalStore } from "react";
import { isLoggedIn, onAuthChange } from "@/lib/auth";

function subscribe(callback: (v: boolean) => void) {
  return onAuthChange(callback);
}

export function useAuth() {
  const loggedIn = useSyncExternalStore<boolean>(
    subscribe,
    () => isLoggedIn(),
    () => false
  );
  return { loggedIn };
}

