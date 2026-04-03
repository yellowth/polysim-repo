/**
 * API / WebSocket base URLs.
 * Local dev: unset VITE_API_URL → http://localhost:8000
 * Production (e.g. Vercel + Railway): set VITE_API_URL=https://your-backend.up.railway.app
 * Optional: VITE_WS_URL=wss://your-backend.up.railway.app (if different from derived from API)
 */
export function getApiBase() {
  const v = import.meta.env.VITE_API_URL;
  if (v && String(v).trim()) return String(v).replace(/\/$/, "");
  return "http://localhost:8000";
}

export function httpUrl(path) {
  const base = getApiBase();
  const p = path.startsWith("/") ? path : `/${path}`;
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
  const wsBase = base.replace(/^http/, "ws");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${wsBase}${p}`;
}

/** Message when fetch/WebSocket fails — explains prod vs local. */
export function apiConnectionErrorHint() {
  const base = getApiBase();
  const where = ` This build calls: ${base}.`;

  if (typeof window === "undefined") {
    return "Could not reach the server." + where;
  }

  const h = window.location.hostname;
  const isLocalHost = h === "localhost" || h === "127.0.0.1";

  // HTTPS page cannot call http:// API (browser mixed-content block)
  if (window.location.protocol === "https:" && base.startsWith("http:")) {
    return (
      "Could not reach the API — use https:// in VITE_API_URL (Railway public URL), not http://." + where
    );
  }

  // Prod site but bundle still has no VITE_API_URL → defaulted to localhost
  if (!isLocalHost && (base.includes("localhost") || base.includes("127.0.0.1"))) {
    return (
      "Could not reach the API — this deploy was built without VITE_API_URL, so it still targets localhost. " +
      "In Vercel: Settings → Environment Variables → add VITE_API_URL = https://(your-railway-app).up.railway.app " +
      "for Production, save, then Deployments → Redeploy (Rebuild)." +
      where
    );
  }

  if (isLocalHost) {
    return (
      "Could not reach the API. Start the backend on port 8000 or run npm run dev (Vite proxies /api)." + where
    );
  }

  return (
    "Could not reach the API. Confirm the backend is up, the URL above is correct, and redeploy after changing VITE_API_URL." +
    where
  );
}
