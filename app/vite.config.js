import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served from https://isabella-law.github.io/uk-legal-ai-audit/
// __BUILD__ changes on every build so browsers never show a stale paper or dataset
export default defineConfig({ plugins: [react()], base: "/uk-legal-ai-audit/", define: { __BUILD__: JSON.stringify(Date.now().toString(36)) } });
