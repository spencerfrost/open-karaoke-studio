import React from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "./App.css";
import App from "./App.tsx";
import { QueryClientProvider } from "@tanstack/react-query";
import queryClient from "./queryClient";
import { logger } from "./lib/logger";

// Log initialization in development
if (import.meta.env.DEV) {
  logger.info(`Logging initialized: level=${logger.getLevel()}`);
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
