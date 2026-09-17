import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: proxy /api to the FastAPI backend on :8000.
// Build: emits static assets into dist/ (served by FastAPI in production).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      // FastAPI's interactive docs live outside /api; proxy them too so the
      // "API docs" link works in dev (otherwise Vite serves the SPA shell).
      "/docs": "http://localhost:8000",
      "/redoc": "http://localhost:8000",
      "/openapi.json": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
