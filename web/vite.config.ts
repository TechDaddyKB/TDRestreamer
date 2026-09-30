import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", proxy: { "/api": "http://127.0.0.1:8080" } },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      reporter: ["text", ["lcov", { projectRoot: ".." }]],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.tsx",
        "src/test-setup.ts",
        "src/generated-api.ts",
      ],
    },
  },
});
