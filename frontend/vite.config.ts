import path from "path";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // Load env variables based on the current mode (development, production, etc.)
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.VITE_BACKEND_URL || "http://localhost:5123";

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: true,
      proxy: {
        "/api": {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
        },
        "/socket.io": {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
          ws: true, // Enable WebSocket proxying
        },
      },
      watch: {
        usePolling: true,
        interval: 1500,
        ignored: [
          path.resolve(__dirname, "../karaoke_library/**"),
          path.resolve(__dirname, "../temp_downloads/**"),
        ],
      },
    },
  };
});
