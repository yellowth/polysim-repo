import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/** Same proxy for `npm run dev` and `npm run preview` so built bundles use relative /api + /ws. */
const localApiProxy = {
  "/api": "http://localhost:8000",
  "/ws": { target: "ws://localhost:8000", ws: true },
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: localApiProxy,
  },
  preview: {
    port: 4173,
    proxy: localApiProxy,
  },
});
