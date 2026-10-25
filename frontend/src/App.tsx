import React from "react";
import { BrowserRouter as Router } from "react-router-dom";

import AppRoutes from "./routes/AppRoutes";
import { SessionProvider } from "./contexts/SessionContext";
import { Toaster } from "./components/ui/sonner";
import { MiniPlayer } from "./components/player/MiniPlayer";
import { useJobsSync } from "./hooks/useJobsSync";
import { useApplyTheme } from "./hooks/useApplyTheme";
import { PWAUpdatePrompt } from "./components/PWAUpdatePrompt";
import { PhonePresence } from "./features/session";

const App: React.FC = () => {
  useJobsSync(); // Sync jobs to processing indicators store
  useApplyTheme();

  return (
    <>
      <Toaster />
      <PWAUpdatePrompt />
      <Router>
        <SessionProvider>
          <AppRoutes />

          {/* Reports this page's presence and opens the controls when this
              device's song starts, whichever page it is on. */}
          <PhonePresence />

          {/* Mini-player renders outside routes, always available */}
          <MiniPlayer />
        </SessionProvider>
      </Router>
    </>
  );
};

export default App;
