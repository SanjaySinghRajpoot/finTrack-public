import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    allowedHosts: ["fintrack.rapidlabs.app", "localhost", "127.0.0.1"],
  },

  plugins: [react()],

  resolve: {
    dedupe: ["react", "react-dom"],
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "lucide-react": "lucide-react/dist/esm/lucide-react",
    },
  },

  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "react-redux",
      "@reduxjs/toolkit",
      "@tanstack/react-query",
      "recharts",
    ],
  },

  build: {
    target: "es2020",
    minify: "esbuild",
    sourcemap: mode === "development",
    chunkSizeWarningLimit: 1000,

    commonjsOptions: {
      transformMixedEsModules: true,
    },

    rollupOptions: {
      output: {
        hoistTransitiveImports: false,

        manualChunks(id) {
          if (id.includes("node_modules/react-router")) return "router";
          if (id.includes("node_modules/@reduxjs")) return "redux";
          if (id.includes("node_modules/@tanstack")) return "query";
          if (id.includes("node_modules/@radix-ui")) return "radix-ui";
          if (id.includes("node_modules/lucide-react")) return "icons";
          if (id.includes("node_modules/date-fns")) return "date";
        },
      },
    },
  },
}));
