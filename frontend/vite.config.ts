import { fileURLToPath } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    /* fileURLToPath e não import.meta.dirname: aquele só existe a partir do
       Node 20.11, e em versões anteriores vira `undefined` — o alias aponta
       para lugar nenhum e todo import de "@/..." quebra. Esta forma funciona
       desde o Node 18. */
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    // Em desenvolvimento o frontend fala com o backend pelo mesmo host, sem CORS.
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
});
