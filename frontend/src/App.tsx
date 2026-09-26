import React from "react";
import { BrowserRouter as Router } from "react-router-dom";

import AppRoutes from "./routes/AppRoutes";
import { SessionProvider } from "./contexts/SessionContext";
import { Toaster } from "./components/ui/sonner";
import { MiniPlayer } from "./components/player/MiniPlayer";
import { useJobsSync } from "./hooks/useJobsSync";
import { PWAUpdatePrompt } from "./components/PWAUpdatePrompt";

const App: React.FC = () => {
  useJobsSync(); // Sync jobs to processing indicators store

  return (
    <>
      <Toaster />
      <PWAUpdatePrompt />
      <Router>
        <SessionProvider>
          <AppRoutes />

          {/* Mini-player renders outside routes, always available */}
          <MiniPlayer />
        </SessionProvider>
      </Router>
    </>
  );
};

export default App;
