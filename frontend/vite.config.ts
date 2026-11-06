import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Browser hits http://localhost:5173; proxy /api and /health to FastAPI (Docker service name or local).
const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": { target: apiProxyTarget, changeOrigin: true },
      "/health": { target: apiProxyTarget, changeOrigin: true },
    },
  },
});
