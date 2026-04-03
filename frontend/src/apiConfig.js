/**
 * API / WebSocket base URLs.
 * - Local dev / preview on localhost: empty base → relative `/api` and `/ws` so Vite’s proxy
 *   (dev server + `vite preview`) forwards to the backend — even for production *builds*
 *   (`import.meta.env.DEV` is false) opened at http://localhost:3000 or :4173.
 * - Hosted production (Vercel, etc.): set VITE_API_URL=https://your-backend…
 * - Optional: VITE_WS_URL
 */
function isBrowserLocalhost() {
  if (typeof window === "undefined") return false;
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1" || h === "[::1]";
}

export function getApiBase() {
  const v = import.meta.env.VITE_API_URL;
  if (v && String(v).trim()) return String(v).replace(/\/$/, "");
  if (import.meta.env.DEV) return "";
  // Production bundle on localhost (vite preview, or old tab) — still use proxy, not :8000 in the browser
  if (isBrowserLocalhost()) return "";
  return "http://localhost:8000";
}

export function httpUrl(path) {
  const base = getApiBase();
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!base) return p;
  return `${base}${p}`;
}

export function wsUrl(path) {
  const explicit = import.meta.env.VITE_WS_URL?.trim();
  if (explicit) {
    const e = explicit.replace(/\/$/, "");
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${e}${p}`;
  }
  const base = getApiBase();
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!base) {
    if (typeof window !== "undefined") {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${window.location.host}${p}`;
    }
    return `ws://localhost:8000${p}`;
  }
  const wsBase = base.replace(/^http/, "ws");
  return `${wsBase}${p}`;
}

/** Message when fetch/WebSocket fails — explains prod vs local. */
export function apiConnectionErrorHint() {
  const base = getApiBase();
  const where = base
    ? ` This build calls: ${base}.`
    : " Vite forwards /api and /ws to http://localhost:8000 — the API process must be listening there.";

  if (typeof window === "undefined") {
    return "Could not reach the server." + where;
  }

  const h = window.location.hostname;
  const isLocalHost =
    h === "localhost" || h === "127.0.0.1" || h === "[::1]";

  // HTTPS page cannot call http:// API (browser mixed-content block)
  if (base && window.location.protocol === "https:" && base.startsWith("http:")) {
    return (
      "Could not reach the API — use https:// in VITE_API_URL (Railway public URL), not http://." + where
    );
  }

  // Prod site but bundle still has no VITE_API_URL → defaulted to localhost
  if (!isLocalHost && base && (base.includes("localhost") || base.includes("127.0.0.1"))) {
    return (
      "Could not reach the API — this deploy was built without VITE_API_URL, so it still targets localhost. " +
      "In Vercel: Settings → Environment Variables → add VITE_API_URL = https://(your-railway-app).up.railway.app " +
      "for Production, save, then Deployments → Redeploy (Rebuild)." +
      where
    );
  }

  if (isLocalHost) {
    return (
      "Could not reach the API. From the repo, start the backend: cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 " +
      "(keep npm run dev running in frontend — it proxies to port 8000)." +
      where
    );
  }

  return (
    "Could not reach the API. Confirm the backend is up, the URL above is correct, and redeploy after changing VITE_API_URL." +
    where
  );
}
