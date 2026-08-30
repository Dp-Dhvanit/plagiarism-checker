import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/analyze":          "http://127.0.0.1:8000",
      "/analyze/image":    "http://127.0.0.1:8000",
      "/health":           "http://127.0.0.1:8000",
      "/upload":           "http://127.0.0.1:8000",
      "/humanize":         "http://127.0.0.1:8000",
      "/detect-code":      "http://127.0.0.1:8000",
      "/detect-code-text": "http://127.0.0.1:8000",
      "/summarize":        "http://127.0.0.1:8000",
      "/history":          "http://127.0.0.1:8000",
      "/dashboard":        "http://127.0.0.1:8000",
      "/report":           "http://127.0.0.1:8000",
    },
  },
});
