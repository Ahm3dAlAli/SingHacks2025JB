export const TOKEN_KEY = "app_token";

type Listener = (loggedIn: boolean) => void;
const listeners: Listener[] = [];

function emit() {
  const state = isLoggedIn();
  listeners.forEach((l) => {
    try {
      l(state);
    } catch {}
  });
}

export function onAuthChange(listener: Listener): () => void {
  listeners.push(listener);
  return () => {
    const idx = listeners.indexOf(listener);
    if (idx >= 0) listeners.splice(idx, 1);
  };
}

export function saveToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
    emit();
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export function logout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    emit();
  }
}

if (typeof window !== "undefined") {
  // Sync across tabs and windows
  window.addEventListener("storage", (e) => {
    if (e.key === TOKEN_KEY) emit();
  });
}
