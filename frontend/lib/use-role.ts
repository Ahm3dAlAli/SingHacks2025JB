"use client";

import { useSyncExternalStore } from "react";

const ROLE_KEY = "app_role";

type AppRole = "relationship_manager" | "compliance_manager" | "legal";

function getRoleValue() {
  if (typeof window === "undefined") return "relationship_manager" as const;
  const r = window.localStorage.getItem(ROLE_KEY) as AppRole | null;
  return r ?? "relationship_manager";
}

function subscribe(callback: () => void) {
  function onStorage(e: StorageEvent) {
    if (e.key === ROLE_KEY) callback();
  }
  if (typeof window !== "undefined") window.addEventListener("storage", onStorage);
  return () => {
    if (typeof window !== "undefined") window.removeEventListener("storage", onStorage);
  };
}

export function useRole() {
  const role = useSyncExternalStore<string>(subscribe, getRoleValue, () => "relationship_manager");
  return { role: role as AppRole };
}

export function saveRole(role: AppRole) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(ROLE_KEY, role);
    window.dispatchEvent(new StorageEvent("storage", { key: ROLE_KEY }));
  }
}
