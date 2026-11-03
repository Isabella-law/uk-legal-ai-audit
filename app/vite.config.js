import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served from https://isabella-law.github.io/uk-legal-ai-audit/
export default defineConfig({ plugins: [react()], base: "/uk-legal-ai-audit/" });
