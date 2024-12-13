import { defineConfig } from "vite";

export default defineConfig({
  build: {
    lib: {
      name: "ha-panel-ingress",
      entry: "src/ha-panel-ingress.ts",
      formats: ["umd"],
      fileName: (fmt, entry) => `${entry}.js`,
    },
  },
});
