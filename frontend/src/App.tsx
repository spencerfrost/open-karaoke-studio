import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import LibraryPage from "./pages/Library";
import AddSongPage from "./pages/AddSong";
import SettingsPage from "./pages/Settings";
import StagePage from "./pages/Stage";
import PerformanceControlsPage from "./pages/PerformanceControlsPage";
import JoinSessionPage from "./pages/JoinSessionPage";
import { SessionProvider } from "./contexts/SessionContext";
import SessionGuard from "./components/SessionGuard";
import { Toaster } from "./components/ui/sonner";
import { MiniPlayer } from "./components/player/MiniPlayer";
import { useJobsSync } from "./hooks/useJobsSync";

const App: React.FC = () => {
  useJobsSync(); // Sync jobs to processing indicators store

  return (
    <>
      <Toaster />
      <Router>
        <SessionProvider>
          <Routes>
            {/* Session entry point - public route */}
            <Route path="/join" element={<JoinSessionPage />} />

            {/* Session-required routes */}
            <Route
              path="/"
              element={
                <SessionGuard>
                  <LibraryPage />
                </SessionGuard>
              }
            />
            <Route
              path="/add"
              element={
                <SessionGuard>
                  <AddSongPage />
                </SessionGuard>
              }
            />
            <Route
              path="/settings"
              element={
                <SessionGuard requireSession={false}>
                  <SettingsPage />
                </SessionGuard>
              }
            />
            <Route
              path="/stage"
              element={
                <SessionGuard deviceType="stage" redirectTo="/stage">
                  <StagePage />
                </SessionGuard>
              }
            />
            <Route
              path="/controls"
              element={
                <SessionGuard deviceType="performer" redirectTo="/controls">
                  <PerformanceControlsPage />
                </SessionGuard>
              }
            />

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>

          {/* Mini-player renders outside routes, always available */}
          <MiniPlayer />
        </SessionProvider>
      </Router>
    </>
  );
};

export default App;
