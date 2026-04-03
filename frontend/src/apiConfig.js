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
  if (typeof window === "undefined") return "Could not reach the server.";
  const h = window.location.hostname;
  if (h === "localhost" || h === "127.0.0.1") {
    return "Could not reach the API. Start the backend (e.g. uvicorn on port 8000) or use npm run dev with the Vite proxy.";
  }
  return "Could not reach the API. Set VITE_API_URL in your frontend host (e.g. Vercel → Environment Variables) to your Railway backend URL, then redeploy — Vite bakes this in at build time.";
}
