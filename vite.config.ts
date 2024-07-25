import { defineConfig } from "vite";

export default defineConfig({
  build: {
    lib: {
      name: "ha-panel-ingress",
      entry: "src/main.ts",
    },
  },
});
