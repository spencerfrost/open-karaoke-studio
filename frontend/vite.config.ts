import path from "path";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig(({ mode }) => {
  // Load env variables based on the current mode (development, production, etc.)
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.VITE_BACKEND_URL || "http://localhost:5123";

  return {
    plugins: [
      react(),
      tailwindcss(),
      VitePWA({
        registerType: "autoUpdate",
        includeAssets: [
          "favicon.ico",
          "apple-touch-icon.png",
          "android-chrome-192x192.png",
          "android-chrome-512x512.png",
        ],
        manifest: {
          name: "Open Karaoke Studio",
          short_name: "OKS",
          description:
            "Your open-source AI powered karaoke studio! Create instrumentals and manage your karaoke library.",
          theme_color: "#fd9a02",
          background_color: "#fd9a02",
          display: "standalone",
          scope: "/",
          start_url: "/",
          orientation: "portrait",
          icons: [
            {
              src: "android-chrome-192x192.png",
              sizes: "192x192",
              type: "image/png",
              purpose: "maskable any",
            },
            {
              src: "android-chrome-512x512.png",
              sizes: "512x512",
              type: "image/png",
              purpose: "maskable any",
            },
          ],
          categories: ["music", "entertainment", "multimedia"],
          lang: "en",
        },
        workbox: {
          globPatterns: ["**/*.{js,css,html,ico,png,svg}"],
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/api\./i,
              handler: "NetworkFirst",
              options: {
                cacheName: "api-cache",
                networkTimeoutSeconds: 10,
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
            {
              urlPattern: /\.(?:png|jpg|jpeg|svg|gif)$/,
              handler: "CacheFirst",
              options: {
                cacheName: "images-cache",
                expiration: {
                  maxEntries: 60,
                  maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
                },
              },
            },
          ],
        },
        devOptions: {
          enabled: true,
        },
      }),
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: true,
      port: 5192,
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
      allowedHosts: ["localhost", "karaoke.mrspinn.ca"],
      watch: {
        usePolling: true,
        interval: 1500,
        ignored: [
          path.resolve(__dirname, "../karaoke_library/**"),
        ],
      },
    },
  };
});
