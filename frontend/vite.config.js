import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Em desenvolvimento o frontend fala com o backend pelo mesmo host, sem CORS.
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
});
